-- v2.3.1 — Player-snapshot Storage bucket (DATA_TRANSFER.md)
-- The pipeline (publish_snapshot.py) writes precomputed, content-hashed, brotli
-- snapshots of the full player universe here; the frontend reads them from the
-- CDN instead of hammering the row API (kills the 500-player ceiling, #2).
--
-- Bucket is PUBLIC: the anon snapshot is identical for every visitor of a scoring
-- profile and carries no user data. Writes are service-role only (the pipeline);
-- service-role bypasses RLS, so only an explicit public-READ policy is needed.
-- Idempotent + safe to re-run.

insert into storage.buckets (id, name, public)
values ('snapshots', 'snapshots', true)
on conflict (id) do update set public = excluded.public;

-- Public (anon + authenticated) read of objects in this bucket only.
drop policy if exists "Public read snapshots" on storage.objects;
create policy "Public read snapshots"
  on storage.objects for select
  to anon, authenticated
  using (bucket_id = 'snapshots');
