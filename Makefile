# Virtual targets
.PHONY: install sandbox

install:
	python setup.py develop
	pip install -r requirements.txt

sandbox: install
	python sandbox/manage.py reset_db --router=default --noinput
	python sandbox/manage.py syncdb --noinput
	python sandbox/manage.py migrate
