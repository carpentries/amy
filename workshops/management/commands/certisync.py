import os
from django.conf import settings
from django.core.management.base import BaseCommand
from workshops.models import Certificate


class Command(BaseCommand):
    args = '/path/to/site'
    help = 'Generate certificates from the database.'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('-r', '--replace',
                            action='store_true',
                            dest='replace',
                            default=False,
                            help='Replace already existing certificates')
        parser.add_argument('-c', '--clean',
                            action='store_true',
                            dest='clean',
                            default=False,
                            help='Delete old PDFs that have been deleted')

    def handle(self, *args, **options):
        if options['clean']:
            self.clean()
        self.generate(**options)

    def arguments(self, certificate):
        args = {
            'badge_type': certificate.badge.name,
            'user_id': certificate.person.username,
            'cert_id': certificate.id,
            'params': {
                'date': certificate.awarded.strftime('%B %d, %Y'),
                'instructor': certificate.get_awarded_by_names(),
                'name': certificate.person.get_full_name(),
            }
        }
        return args

    def clean(self):
        """Delete PDFs of old certificates that have been
           deleted from the database"""

        all_certs = Certificate.objects.all()
        listdir = os.listdir(settings.CERTIFICATES_DIR)
        old_certs = set(x for x in listdir if x.endswith('pdf'))
        new_certs = set(str(x.id)+'.pdf' for x in all_certs)
        to_be_deleted = old_certs - new_certs
        for x in to_be_deleted:
            filename = os.path.join(settings.CERTIFICATES_DIR, x)
            os.remove(filename)
            print('Deleted ' + filename)

    def generate(self, **options):
        """Generate certificate PDFs from the database"""

        from certification.code import certificates

        certis = Certificate.objects.all()
        for cert in certis:
            filename = os.path.join(settings.CERTIFICATES_DIR,
                                    str(cert.id) + '.pdf')
            if os.path.isfile(filename) and not options['replace']:
                continue
            args = self.arguments(cert)
            certificates.generate(args)
            print('Generated ' + filename)
