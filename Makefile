.PHONY: all clean

all:
	python run_all.py

clean:
	-rm -rf data/raw data/processed outputs
