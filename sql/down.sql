-- Rise Archived Status — rollback
-- WARNING: projects currently set to Archived will lose their status.

DELETE FROM rise_project_status WHERE key_name = 'archived';
