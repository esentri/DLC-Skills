#!/usr/bin/env python3
"""Generate `claude plugin eval` cases from evals/suite.json.

Each case gets its own directory under evals/cases/ with
  case.yaml  - prompt, limits and graders
  setup.sh   - scaffold script creating a small Java project in the given mode

Case fields (suite.json):
  id, mode (none|A|B|C|C-JDBC), prompt, expect, forbid ("*" = all skills), reads, note
  section   triggering | negative | agents-md | rules (default from expect)
  agents    overrides for AGENTS.md lines, e.g. {"Event publishing": "..."};
            {"loading_line": false} drops the skill-loading line,
            {"Mode": "A"} switches to the plain-DDD AGENTS.md
  legacy    true -> scaffold an additional legacy context (umschreibungen)
  extra_deps   [[group, artifact, version|null], ...] added to the pom
  extra_files  {path: content} added to the sample project
  answer_must / answer_must_not
            regexes over the final answer (string or {"pattern", "flags"})
  judge     list of PASS/FAIL rubrics for an LLM judge over the final answer
Cases with answer_* or judge ask for the code in the answer instead of writing files.

Run after editing suite.json:  python3 evals/generate.py
Stdlib only (no PyYAML needed): YAML is written by hand, strings as JSON
double-quoted scalars (valid YAML).
"""
import json
import re
import shutil
from pathlib import Path

EVALS = Path(__file__).resolve().parent
CASES = EVALS / "cases"

ALL_SKILLS = [
    "ddd-tactical-java", "domainlifecycles", "dlc-persistence-schema",
    "dlc-impact-analysis", "dlc-diagrammer", "dlc-diagram-viewer", "dlc-project-setup", "new-aggregate",
]
# new-aggregate has disable-model-invocation: Claude Code must never load it on its own.
ALWAYS_FORBIDDEN = ["new-aggregate"]

RUNS = 3
MAX_TURNS = 8
MAX_TURNS_CODE = 12
TIMEOUT_SECONDS = 240
TIMEOUT_SECONDS_CODE = 360
# Appended to every prompt: runs stay read-only, short and cheap. Triggering cases
# only need the plan; rule cases need the code in the answer to grade it.
PROMPT_SUFFIX = "\n\nDo not modify any files - explain how you would do it."
# The LLM judge only sees an excerpt from the start of the answer - so the answer
# starts with a short design summary the judge can grade.
PROMPT_SUFFIX_CODE = ("\n\nDo not modify any files. Start your answer with a design summary of at most "
                      "6 bullet points (which classes / building blocks, in which packages, who calls "
                      "whom, which checks happen where). Then show the complete code (and SQL, if "
                      "needed) of your solution, with package declarations.")


def q(s: str) -> str:
    """YAML double-quoted scalar (JSON string syntax is valid YAML)."""
    return json.dumps(s, ensure_ascii=False)


def skill_regex(names):
    alt = "|".join(names)  # skill names are [a-z-], no escaping needed
    return r'"skill"\s*:\s*"(?:[\w-]+:)?(?:' + alt + r')"'


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40].rstrip("-")


# ---------------------------------------------------------------- scaffolds

LOADING_A = "For any work on domain code, load the skill `ddd-tactical-java` first."
LOADING_BC = ("For any work on domain code, load the skills `ddd-tactical-java` and\n"
              "`domainlifecycles` first (Mode A: only `ddd-tactical-java`).")


def agents_md(mode: str, overrides: dict) -> str:
    """AGENTS.md as in templates/AGENTS.md.snippet, with per-case overrides."""
    overrides = dict(overrides or {})
    loading = overrides.pop("loading_line", True)
    mode = overrides.get("Mode", mode)
    if mode == "A":
        fields = {"Mode": "A", "Domain base package": "com.example.shop",
                  "Validation style": "Java exceptions (no DLC)", "Package layout": "default"}
        line = LOADING_A
    else:
        fields = {"Mode": mode, "Domain base package": "com.example.shop",
                  "Persistence": {"C": "jOOQ", "C-JDBC": "JDBC"}.get(mode, "none"),
                  "Validation style": "DomainAssertions", "Event publishing": "DomainEvents",
                  "Package layout": "default", "Legacy contexts": "none"}
        line = LOADING_BC
    fields.update(overrides)
    out = ["## DomainLifeCycles"] + ([line] if loading else [])
    out += [f"{k}: {v}" for k, v in fields.items()]
    return "\n".join(out) + "\n"

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
{parent}  <groupId>com.example</groupId>
  <artifactId>shop</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <properties><java.version>21</java.version>{props}</properties>
  <dependencies>
{deps}  </dependencies>
</project>
"""

# Mode C uses the newest supported stack: Spring Boot 4.x with the DLC
# `spring-boot-starter` on Java 21 (jOOQ version managed by Spring Boot).
BOOT_PARENT = """  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>4.1.1</version>
  </parent>
"""
BOOT_PROPS = ""


def dep(group, artifact, version=None):
    v = f"<version>{version}</version>" if version else ""
    return f"    <dependency><groupId>{group}</groupId><artifactId>{artifact}</artifactId>{v}</dependency>\n"


ORDER_A = """package com.example.shop.order.core.domain;

import java.util.Objects;
import java.util.UUID;

public final class Order {
    public record OrderId(UUID value) {}
    private final OrderId id;
    private OrderStatus status;

    public Order(OrderId id, OrderStatus status) {
        this.id = Objects.requireNonNull(id);
        this.status = Objects.requireNonNull(status);
    }

    public void cancel() {
        if (status != OrderStatus.PENDING) throw new IllegalStateException("Only pending orders can be cancelled.");
        status = OrderStatus.CANCELLED;
    }
}
"""

ORDER_DLC = """package com.example.shop.order.core.domain;

import io.domainlifecycles.assertion.DomainAssertions;
import io.domainlifecycles.domain.types.Identity;
import io.domainlifecycles.domain.types.base.AggregateRootBase;
import lombok.Builder;
import lombok.Getter;

@Getter
public final class Order extends AggregateRootBase<Order.OrderId> {
    public record OrderId(Long value) implements Identity<Long> {}
    private final OrderId id;
    private OrderStatus status;

    @Builder
    public Order(long concurrencyVersion, OrderId id, OrderStatus status) {
        super(concurrencyVersion);
        this.id = id;
        this.status = status;
        validate();
    }

    public Order cancel() {
        DomainAssertions.equals(status, OrderStatus.PENDING, "Only pending orders can be cancelled.");
        status = OrderStatus.CANCELLED;
        return this;
    }
}
"""

STATUS = """package com.example.shop.order.core.domain;

public enum OrderStatus { PENDING, SHIPPED, CANCELLED }
"""

PACKAGE_INFO = """@BoundedContext("Order")
package com.example.shop.order;

import io.domainlifecycles.domain.types.BoundedContext;
"""

APP_C = """package com.example.shop;

import io.domainlifecycles.autoconfig.annotation.EnableDlc;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@EnableDlc(dlcMirrorBasePackages = "com.example.shop", jooqRecordPackage = "com.example.shop.jooq.tables.records")
@SpringBootApplication
public class ShopApplication {
    public static void main(String[] args) { SpringApplication.run(ShopApplication.class, args); }
}
"""

SERVICE_C = """package com.example.shop.order.core.application;

import com.example.shop.order.core.domain.Order;
import io.domainlifecycles.domain.types.ApplicationService;

public class OrderService implements ApplicationService {
    public Order placeOrder(PlaceOrder command) { throw new UnsupportedOperationException("todo"); }
}
"""

COMMAND_C = """package com.example.shop.order.core.application;

import io.domainlifecycles.domain.types.DomainCommand;

public record PlaceOrder(Long customerId) implements DomainCommand {}
"""

LOGBACK = """<configuration>
  <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder><pattern>%d %-5level %logger - %msg%n</pattern></encoder>
  </appender>
  <root level="INFO"><appender-ref ref="CONSOLE"/></root>
</configuration>
"""

SRC = "src/main/java/com/example/shop"
DOMAIN = f"{SRC}/order/core/domain"

# Legacy context with a deliberately different, non-DDD structure (anemic, setters,
# service with logic, no core/ packages) - see "Legacy contexts" in AGENTS.md.
LEGACY = {
    f"{SRC}/umschreibungen/Umschreibung.java": """package com.example.shop.umschreibungen;

public class Umschreibung {
    private Long id;
    private String vertragsnummer;
    private String neuerInhaber;
    private String status;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getVertragsnummer() { return vertragsnummer; }
    public void setVertragsnummer(String vertragsnummer) { this.vertragsnummer = vertragsnummer; }
    public String getNeuerInhaber() { return neuerInhaber; }
    public void setNeuerInhaber(String neuerInhaber) { this.neuerInhaber = neuerInhaber; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
""",
    f"{SRC}/umschreibungen/UmschreibungService.java": """package com.example.shop.umschreibungen;

import org.springframework.stereotype.Service;

@Service
public class UmschreibungService {
    private final UmschreibungDao dao;

    public UmschreibungService(UmschreibungDao dao) { this.dao = dao; }

    public void abschliessen(Long id) {
        Umschreibung u = dao.load(id);
        if (!"OFFEN".equals(u.getStatus())) throw new IllegalStateException("not open");
        u.setStatus("ABGESCHLOSSEN");
        dao.save(u);
    }
}
""",
    f"{SRC}/umschreibungen/UmschreibungDao.java": """package com.example.shop.umschreibungen;

public interface UmschreibungDao {
    Umschreibung load(Long id);
    void save(Umschreibung umschreibung);
}
""",
}


def files_for(c: dict) -> dict:
    mode = c["mode"]
    extra = "".join(dep(g, a, v) for g, a, v in c.get("extra_deps", []))
    files = base_files(mode, extra)
    if "AGENTS.md" in files or c.get("agents"):
        files["AGENTS.md"] = agents_md(mode, c.get("agents"))
    if c.get("legacy"):
        files.update(LEGACY)
    files.update(c.get("extra_files", {}))
    return files


def base_files(mode: str, extra: str = "") -> dict:
    if mode == "none":
        return {"pom.xml": POM.format(parent="", props="", deps=extra)}
    if mode == "A":
        return {
            "pom.xml": POM.format(parent="", props="", deps=extra),
            "AGENTS.md": "",
            f"{DOMAIN}/Order.java": ORDER_A,
            f"{DOMAIN}/OrderStatus.java": STATUS,
        }
    dlc = "3.5.0"
    if mode == "B":
        deps = (dep("io.domainlifecycles", "types", dlc) + dep("io.domainlifecycles", "type-utils", dlc)
                + dep("io.domainlifecycles", "assertions", dlc) + dep("org.projectlombok", "lombok", "1.18.48")
                + extra)
        return {
            "pom.xml": POM.format(parent="", props="", deps=deps),
            "AGENTS.md": "",
            f"{SRC}/order/package-info.java": PACKAGE_INFO,
            f"{DOMAIN}/Order.java": ORDER_DLC,
            f"{DOMAIN}/OrderStatus.java": STATUS,
        }
    if mode in ("C", "C-JDBC"):
        jdbc = mode == "C-JDBC"
        deps = (dep("io.domainlifecycles", "spring-boot-starter", dlc)
                + dep("org.springframework.boot", "spring-boot-starter-webmvc")
                + dep("org.springframework.boot", "spring-boot-starter-jdbc" if jdbc else "spring-boot-starter-jooq")
                + (dep("org.postgresql", "postgresql") if jdbc else "")
                + dep("org.springframework.boot", "spring-boot-starter-flyway")
                + dep("org.projectlombok", "lombok")
                + extra)
        app = APP_C.replace('jooqRecordPackage = "com.example.shop.jooq.tables.records"',
                            'jooqSqlDialect = "POSTGRES"') if jdbc else APP_C
        return {
            "pom.xml": POM.format(parent=BOOT_PARENT, props=BOOT_PROPS, deps=deps),
            "AGENTS.md": "",
            f"{SRC}/ShopApplication.java": app,
            f"{SRC}/order/package-info.java": PACKAGE_INFO,
            f"{DOMAIN}/Order.java": ORDER_DLC,
            f"{DOMAIN}/OrderStatus.java": STATUS,
            f"{SRC}/order/core/application/OrderService.java": SERVICE_C,
            f"{SRC}/order/core/application/PlaceOrder.java": COMMAND_C,
            "src/main/resources/logback.xml": LOGBACK,
            "src/main/resources/db/migration/V1__order.sql":
                "CREATE TABLE \"order\" (id BIGINT PRIMARY KEY, concurrency_version BIGINT NOT NULL, status VARCHAR(50) NOT NULL);\n"
                "CREATE SEQUENCE order_id_seq START WITH 1000;\n",
        }
    raise ValueError(f"unknown mode {mode}")


def setup_script(c: dict) -> str:
    out = ["#!/usr/bin/env bash", "# Generated by evals/generate.py - do not edit.",
           f"# Scaffolds a mode-{c['mode']} sample project into the eval workspace (cwd).", "set -euo pipefail"]
    for i, (path, content) in enumerate(files_for(c).items()):
        marker = f"EOF_{i}"
        out.append(f'mkdir -p "$(dirname "{path}")"')
        out.append(f"cat > \"{path}\" <<'{marker}'\n{content.rstrip()}\n{marker}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ cases

def section_of(c: dict) -> str:
    if c.get("section"):
        return c["section"]
    return "negative" if not c["expect"] else "triggering"


def is_code_case(c: dict) -> bool:
    return bool(c.get("answer_must") or c.get("answer_must_not") or c.get("judge"))


def regex_spec(r):
    return (r, None) if isinstance(r, str) else (r["pattern"], r.get("flags"))


def case_yaml(c: dict, name: str) -> str:
    section = section_of(c)
    code = is_code_case(c)
    forbid = list(c.get("forbid", []))
    if "*" in forbid:
        forbid = ALL_SKILLS
    forbid = sorted(set(forbid + ALWAYS_FORBIDDEN))
    lines = [
        'schema_version: "1.1"',
        f"name: {q(name)}",
        f"description: {q((c.get('note') or 'eval #' + str(c['id'])) + ' (mode ' + c['mode'] + ')')}",
        f"tags: [{section}, mode-{c['mode'].lower()}]",
        f"runs: {RUNS}",
        "execution:",
        f"  prompt: {q(c['prompt'] + (PROMPT_SUFFIX_CODE if code else PROMPT_SUFFIX))}",
        f"  max_turns: {MAX_TURNS_CODE if code else MAX_TURNS}",
        f"  timeout_seconds: {TIMEOUT_SECONDS_CODE if code else TIMEOUT_SECONDS}",
        "  allowed_tools: [Read, Glob, Grep, Skill]",
        "context:",
        "  scaffold_script: setup.sh",
        "graders:",
    ]
    for s in c["expect"]:
        lines += [
            f"  - name: {q('loads ' + s)}",
            "    type: tool_used",
            "    tool: Skill",
            f"    input_match: {q(skill_regex([s]))}",
            "    min: 1",
            "    arm: both",
        ]
    for s in forbid:
        lines += [
            f"  - name: {q('does not load ' + s)}",
            "    type: tool_used",
            "    tool: Skill",
            f"    input_match: {q(skill_regex([s]))}",
            "    min: 0",
            "    max: 0",
            "    arm: both",
        ]
    for r in c.get("reads", []):
        lines += [
            f"  - name: {q('reads ' + r)}",
            "    type: tool_used",
            "    tool: Read",
            f"    input_match: {q('references/' + r.replace('.', '[.]'))}",
            "    min: 1",
            "    weight: 0.5",
            "    arm: both",
        ]
    for kind, items in (("contains", c.get("answer_must", [])), ("not_contains", c.get("answer_must_not", []))):
        for r in items:
            pattern, flags = regex_spec(r)
            label = ("answer contains " if kind == "contains" else "answer does not contain ") + pattern
            lines += [
                f"  - name: {q(label[:80])}",
                "    type: regex",
                f"    pattern: {q(pattern)}",
            ]
            if flags:
                lines.append(f"    flags: {q(flags)}")
            if kind == "not_contains":
                lines.append("    match: not_contains")
            lines.append("    arm: both")
    for i, crit in enumerate(c.get("judge", []), 1):
        lines += [
            f"  - name: {q('judge ' + str(i))}",
            "    type: llm",
            f"    criteria: {q(crit)}",
            "    arm: both",
        ]
    return "\n".join(lines) + "\n"


def main():
    spec = json.loads((EVALS / "suite.json").read_text())
    if CASES.exists():
        shutil.rmtree(CASES)
    for c in spec["cases"]:
        unknown = [s for s in c["expect"] + c.get("forbid", []) if s != "*" and s not in ALL_SKILLS]
        if unknown:
            raise SystemExit(f"case {c['id']}: unknown skills {unknown}")
        prefix = {"triggering": "t", "negative": "n", "agents-md": "a", "rules": "r"}[section_of(c)]
        name = f"{prefix}{c['id']:02d}-{slug(c['prompt'])}"
        d = CASES / name
        d.mkdir(parents=True)
        (d / "case.yaml").write_text(case_yaml(c, name))
        sh = d / "setup.sh"
        sh.write_text(setup_script(c))
        sh.chmod(0o755)
    print(f"generated {len(spec['cases'])} cases in {CASES.relative_to(EVALS.parent)}")


if __name__ == "__main__":
    main()
