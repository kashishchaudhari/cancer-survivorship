"""Backward-compatible Liver entry point for the cohort bootstrap evaluator."""
import argparse
from pathlib import Path
from evaluate_cohort_uncertainty import evaluate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--studies", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".runtime/liver-uncertainty.json"))
    args = parser.parse_args()
    evaluate(args.folder, args.studies, args.output, "Liver")
