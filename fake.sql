-- schema is (serial_number, notes, organizer_id[site], project_id[project], site_id[site])

insert into workshops_pending
select 1, 'no notes as yet', site_a.id, p.id, site_b.id
from workshops_site site_a, workshops_project p, workshops_site site_b
where site_a.domain='amric.ca' and p.slug='SWC' and site_b.domain='amric.ca';

insert into workshops_pending
select 2, 'no notes yet', site_a.id, p.id, site_b.id
from workshops_site site_a, workshops_project p, workshops_site site_b
where site_a.domain='asu.edu' and p.slug='SWC' and site_b.domain='caltech.edu';

insert into workshops_pending
select 3, 'no notes yet', site_a.id, p.id, site_b.id
from workshops_site site_a, workshops_project p, workshops_site site_b
where site_a.domain='asu.edu' and p.slug='DC' and site_b.domain='clemson.edu';
