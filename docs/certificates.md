Managing Certificates
=======================

> The code used to generate certificates is based on the [certification repository](https://github.com/swcarpentry/certification/), located in
`certification/code/certificates.py`

### Certification Workflow

* To award a certificate to a person, go to the `Persons` page, click on their name, click on `Edit` and select the `Certificates` tab.
* Enter the relevant details, and click on `Add`
>Doing this will only create an entry in the certificates database. The certificate PDF is still not available for download.

* To generate the certificate PDFs, use the `certisync` command
* Once the certificate has been generated, it is available for download via the download link.
>An error message is displayed if the certificate hasn't been generated yet

### The `certisync` command

The `certisync` command generates PDF copies of certificates from the database. All certificates are stored in `CERTIFICATES_DIR` as defined in `settings.py`

##### Usage

##### `python manage.py certisync`

Doing so will generate any new certificates that have been added to the database since its last usage. Note that this does not delete or update already existing certificates

##### Flags

* ##### `-c`, `--clean`

Deletes obsolete certificates from the `CERTIFICATES_DIR` that have been deleted from the database.

* ##### `-r`, `--replace`

Replace already existing certificates in the `CERTIFICATES_DIR`
