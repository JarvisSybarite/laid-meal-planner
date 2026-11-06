.PHONY: build-PlannerFunction
build-PlannerFunction:
	python3 -m pip install -r requirements.txt -t "$(ARTIFACTS_DIR)"
	cp app.py handler.py "$(ARTIFACTS_DIR)/"
