"""Performance benchmarking utilities for MEPS PySpark migration."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import psutil


@dataclass
class StageMetric:
    """Metrics captured at a single ETL stage."""

    stage_name: str
    row_count: int
    wall_clock_seconds: float
    memory_mb: float


@dataclass
class JobBenchmark:
    """Performance benchmark for a complete ETL job."""

    job_name: str
    complexity_tier: str
    input_files: List[str] = field(default_factory=list)
    stages: List[StageMetric] = field(default_factory=list)
    total_wall_clock_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    output_row_count: int = 0
    num_join_operations: int = 0
    input_file_sizes_mb: Dict[str, float] = field(default_factory=dict)
    output_parquet_path: str = ""

    def add_stage(self, stage_name: str, row_count: int, elapsed: float) -> None:
        """Record metrics for a completed ETL stage."""
        mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        self.stages.append(
            StageMetric(
                stage_name=stage_name,
                row_count=row_count,
                wall_clock_seconds=elapsed,
                memory_mb=mem_mb,
            )
        )
        if mem_mb > self.peak_memory_mb:
            self.peak_memory_mb = mem_mb

    def to_dict(self) -> Dict:
        """Convert benchmark to a dictionary for report generation."""
        return {
            "job_name": self.job_name,
            "complexity_tier": self.complexity_tier,
            "input_files": self.input_files,
            "total_wall_clock_seconds": self.total_wall_clock_seconds,
            "peak_memory_mb": self.peak_memory_mb,
            "output_row_count": self.output_row_count,
            "num_join_operations": self.num_join_operations,
            "input_file_sizes_mb": self.input_file_sizes_mb,
            "output_parquet_path": self.output_parquet_path,
            "stages": [
                {
                    "stage_name": s.stage_name,
                    "row_count": s.row_count,
                    "wall_clock_seconds": s.wall_clock_seconds,
                    "memory_mb": s.memory_mb,
                }
                for s in self.stages
            ],
        }


class BenchmarkTimer:
    """Context manager for timing ETL stages."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "BenchmarkTimer":
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed = time.time() - self._start
