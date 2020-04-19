from rq.job import Job as _Job


class Job(_Job):
    def set_status(self, status, *args, **kwargs):
        from autoemails.models import RQJob

        # update status in parent class
        result = super().set_status(status, *args, **kwargs)

        # update DB
        RQJob.objects.filter(job_id=self.get_id()).update(status=status)

        return result
