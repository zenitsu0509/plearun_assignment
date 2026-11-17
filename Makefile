.PHONY: test sample

test:
	python3 -m unittest discover -s tests -v

sample:
	python3 plearun_cli.py reports/report_fictional_02.txt records > findings.json
