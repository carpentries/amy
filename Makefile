all : commands

## commands     : show all commands.
commands : Makefile
	@sed -n 's/^## //p' $<

## migrations   : create/apply migrations
migrations :
	python manage.py makemigrations
	python manage.py migrate

## clean        : clean up.
clean :
	rm -f $$(find . -name '*~' -print) $$(find . -name '*.pyc' -print)
