-- Reset all ETL jobs to READY status with all steps set to idle
UPDATE etl_jobs
SET status = jsonb_build_object(
    'overall', 'READY'::text,
    'token', NULL,
    'steps', (
        SELECT jsonb_object_agg(
            step_name,
            jsonb_build_object(
                'order', (status->'steps'->step_name->>'order')::int,
                'display_name', status->'steps'->step_name->>'display_name',
                'extraction', 'idle'::text,
                'transform', 'idle'::text,
                'embedding', 'idle'::text
            )
        )
        FROM jsonb_object_keys(status->'steps') AS step_name
    )
);

-- Verify the update
SELECT 
    id, 
    job_name, 
    status->'overall' as overall_status,
    jsonb_pretty(status->'steps') as steps_status
FROM etl_jobs 
WHERE tenant_id = 1 
ORDER BY id;

