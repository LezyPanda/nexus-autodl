NAME:=nexus_autodl

all: build

build: run.py
	pyinstaller --clean --noconsole -F $<

clean:
	$(RM) -r build dist *.spec

.PHONY: build clean
