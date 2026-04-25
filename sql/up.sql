-- Rise Audio Recording Addon
-- Enables in-browser voice recording in tasks, notes, and todos

INSERT INTO rise_settings (setting_name, setting_value)
VALUES ('enable_audio_recording', '1')
ON DUPLICATE KEY UPDATE setting_value = '1';
