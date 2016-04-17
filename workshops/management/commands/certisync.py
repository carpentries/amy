import os
import sys
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
        parser.add_argument('-s', '--sync-only',
                            action='store_true',
                            dest='sync-only',
                            default=False,
                            help='Only sync the database without generating \
                            new certificates')

    def handle(self, *args, **options):
        self.check_flags(options)

        if options['clean']:
            self.clean()

        certis = Certificate.objects.all()
        for cert in certis:
            filepath = os.path.join(settings.CERTIFICATES_DIR,
                                    str(cert.id) + '.pdf')
            # skip generation if certificate already exists or if -s is set
            # but not if the -r flag is set
            if (os.path.isfile(filepath) and not options['replace']) or\
               options['sync-only']:
                self.syncdb(cert, filepath)
                continue
            self.generate(cert)
            self.syncdb(cert, filepath)
            print('Generated ' + filepath)

    def check_flags(self, options):
        """Terminate if -s and -r flags are set together."""
        if options['replace'] and options['sync-only']:
            print('Error: cannot use the -s and -r flags together.',
                  file=sys.stderr)
            sys.exit(1)

    def arguments(self, certificate):
        """Generate arguments from certificate object"""
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
           deleted from the database."""
        all_certs = Certificate.objects.all()
        listdir = os.listdir(settings.CERTIFICATES_DIR)
        old_certs = set(x for x in listdir if x.endswith('pdf'))
        new_certs = set(str(x.id)+'.pdf' for x in all_certs)
        to_be_deleted = old_certs - new_certs
        for x in to_be_deleted:
            filepath = os.path.join(settings.CERTIFICATES_DIR, x)
            os.remove(filepath)
            print('Deleted ' + filepath)

    def generate(self, certificate):
        """Generate certificate PDFs from the database."""
        from certification.code import certificates
        args = self.arguments(certificate)
        certificates.generate(args)

    def syncdb(self, cert, filepath):
        """Update download_ready field in the database."""
        if os.path.isfile(filepath):
            if not cert.download_ready:
                cert.download_ready = True
                cert.save()
                print('Synced ' + filepath)
        else:
            if cert.download_ready:
                cert.download_ready = False
                cert.save()
                print('Synced ' + filepath)
