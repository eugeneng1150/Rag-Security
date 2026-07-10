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

    @property
    def abs_results_dir(self):
        return os.path.join(PROJECT_ROOT, self.results_dir)


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    attacks: AttacksConfig = field(default_factory=AttacksConfig)
    defense: DefenseConfig = field(default_factory=DefenseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def load_config(path=None) -> Config:
    if path is None:
        path = os.path.join(PROJECT_ROOT, "config.yaml")

    with open(path) as f:
        raw = yaml.safe_load(f)

    return Config(
        model=ModelConfig(**raw.get("model", {})),
        database=DatabaseConfig(**raw.get("database", {})),
        attacks=AttacksConfig(**raw.get("attacks", {})),
        defense=DefenseConfig(**raw.get("defense", {})),
        logging=LoggingConfig(**raw.get("logging", {})),
    )
