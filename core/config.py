import os
import yaml
from dataclasses import dataclass, field
from typing import List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class ModelConfig:
    base_url: str = "http://localhost:8080/v1"
    api_key: str = "not-needed"
    model_name: str = "qwen"
    temperature: float = 0.0
    max_tokens: int = 2048


@dataclass
class DatabaseConfig:
    path: str = "data/employee.db"
    seed_employees: int = 20
    seed_private: int = 20

    @property
    def abs_path(self):
        return os.path.join(PROJECT_ROOT, self.path)


@dataclass
class AttacksConfig:
    categories: List[str] = field(default_factory=lambda: [
        "blocker", "compliance_framing", "fixed_output_structure", "combined"
    ])
    num_trials: int = 10


@dataclass
class DefenseConfig:
    anomaly_threshold: float = 0.5
    max_claims_per_response: int = 10


@dataclass
class LoggingConfig:
    results_dir: str = "results"
    verbose: bool = True
    active_model: str = "qwen"

    @property
    def abs_results_dir(self):
        return os.path.join(PROJECT_ROOT, self.results_dir, self.active_model)


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    attacks: AttacksConfig = field(default_factory=AttacksConfig)
    defense: DefenseConfig = field(default_factory=DefenseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(path=None, model_override=None) -> Config:
    if path is None:
        path = os.path.join(PROJECT_ROOT, "config.yaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    active = model_override or raw.get("active_model", "qwen")
    models = raw.get("models", {})
    if active not in models:
        available = ", ".join(models.keys())
        raise ValueError(f"Model '{active}' not found in config. Available: {available}")
    model_raw = models.get(active)

    logging_raw = raw.get("logging", {})
    logging_raw["active_model"] = active

    db_raw = raw.get("database", {})
    db_raw["path"] = f"data/employee_{active}.db"

    config = Config(
        model=ModelConfig(**model_raw),
        database=DatabaseConfig(**db_raw),
        attacks=AttacksConfig(**raw.get("attacks", {})),
        defense=DefenseConfig(**raw.get("defense", {})),
        logging=LoggingConfig(**logging_raw),
    )

    os.makedirs(config.logging.abs_results_dir, exist_ok=True)
    for phase in ["phase0", "phase1", "phase2", "phase3"]:
        os.makedirs(os.path.join(config.logging.abs_results_dir, phase), exist_ok=True)

    return config


def parse_model_arg():
    """Parse --model flag from command line args. Returns model name or None."""
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--model", type=str, default=None,
                        help="Model to use: e.g. 'qwen' or 'deepseek'")
    args, _ = parser.parse_known_args()
    return args.model
