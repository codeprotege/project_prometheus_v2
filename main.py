#!/usr/bin/env python3
import argparse
import nltk
from app.orchestrator import run_pipeline
from app.utils.config_loader import load_cfg

def main():
    parser = argparse.ArgumentParser(description="Patent analytics with WSOA")
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--keyword', help='Run keyword mode instead of CPC list')
    parser.add_argument('--max_patents', type=int, help='Override max patents')
    args = parser.parse_args()

    cfg = load_cfg(args.config)
    if args.max_patents: cfg['sources']['max_patents'] = args.max_patents

    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt_tab', quiet=True)

    run_pipeline(cfg, args.keyword)

if __name__ == "__main__":
    main()