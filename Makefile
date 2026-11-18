.PHONY: all clean

all:
	python src/fetch.py
	python src/tidy.py
	python src/checks.py
	python src/metrics.py
	python src/analysis.py
	python src/talent.py
	python src/report.py

clean:
	-rm -rf data/raw data/processed outputs
