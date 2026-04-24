-- Rise Archived Status — schema migration (safe to run multiple times)
-- Adds an "Archived" project status for abandoned/non-payment projects.
-- Keeps records for tax and history without hard-deleting.

INSERT IGNORE INTO rise_project_status (id, key_name, title, icon, order_by, color)
VALUES (6, 'archived', 'Archived', 'archive', 6, '#888888');
