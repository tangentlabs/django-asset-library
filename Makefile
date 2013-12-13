# Virtual targets
.PHONY: install sandbox

install:
	python setup.py develop
	pip install -r requirements.txt

sandbox: install
	python sites/sandbox/manage.py reset_db --router=default --noinput
	python sites/sandbox/manage.py syncdb --noinput
	python sites/sandbox/manage.py migrate
