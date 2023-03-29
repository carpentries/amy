# Production database backups

Production database is backed-up by AWS with two of their services:

1. [AWS Relational Database Service (RDS)](https://aws.amazon.com/rds/) snapshots and backups
2. [AWS Backup](https://aws.amazon.com/backup/).

Additional backups are:

1. created before starting any deployment starts
2. automatically run via a cronjob on the server.

## Backup system

Both services back the database by creating snapshots. They are incremental and allow
to restore the database as a complete service. So it doesn't matter which PostgreSQL
database is restored, it will be the whole server as a new instance.

## AWS Relational Database Service (RDS)

The database is set up to have a daily snapshot around 7 AM UTC. The rentention period
is 35 days, and older snapshots are deleted.

## AWS Backup

This is an additional backup service. It also makes daily snapshots of the database, and
they also have a rentention of 35 days. The difference is in longer time period.
After 35 days, AWS Backup keeps one snapshot per month.

## Deployment backups

Additional backups are created before starting any deployment with `pg_dump`. They are
stored locally on the server.

A good practice is to create a manual snapshot in AWS console before starting
a deployment. Manual snapshots are not deleted automatically.

## Automatic backup from inside of the server

A script is set up to run every 30 minutes and upload a `pg_dump` of the database to S3.
