
git clone git@jugit.fz-juelich.de:jutrack/jtrack-dashboard2.git
pip install -r requirements.txt
mysql -u jtrackuser -p'jtrackuser@JDASH123' jtrack < jtrack.sql
python manage.py createsuperuser
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
python manage.py runserver
