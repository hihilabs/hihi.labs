#!/usr/bin/env python3
"""
Patch app/Views/includes/timeline_preview.php
Adds seperate_audio support: recording-*.webm files render as inline <audio>
elements above other attachments, with id-based hash anchors for deep-linking.
"""
import os, sys

RISE_ROOT = os.environ.get("RISE_ROOT", os.getcwd())
TARGET = os.path.join(RISE_ROOT, "app/Views/includes/timeline_preview.php")

MARKER = "seperate_audio"
INJECT = """\
        if (isset($seperate_audio) && $seperate_audio && $extension === "webm" && strpos($file_name, 'recording')) {

            $actual_file_name_without_extension = remove_file_extension($actual_file_name);

            $recording_files .= "<audio src='$url' controls='' class='audio file-highlight-section' id='$actual_file_name_without_extension'></audio>";

        } else {\
"""

SCROLL_MARKER = "file-highlight-link"
SCROLL_INJECT = """\
<script>
    $(document).ready(function() {
        $(".file-highlight-link").click(function(e) {
            var fileId = $(this).attr('data-file-id');

            e.preventDefault();

            highlightSpecificFile(fileId);
        });

        function highlightSpecificFile(fileId) {
            $(".file-highlight-section").removeClass("file-highlight");
            $("#recording-" + fileId).addClass("file-highlight");
            window.location.hash = ""; //remove first to scroll with main link
            window.location.hash = "recording-" + fileId;
        }

    });
</script>\
"""

with open(TARGET, "r") as f:
    content = f.read()

changed = False

if MARKER not in content:
    # Find the else block after extension checks and inject before it
    old = '            } else {\n\n                if (is_viewable_image_file($file_name)) {'
    new = INJECT + '\n\n                if (is_viewable_image_file($file_name)) {'
    if old in content:
        content = content.replace(old, new, 1)
        changed = True
    else:
        print(f"ERROR: Could not find injection point in {TARGET}")
        sys.exit(1)
else:
    print(f"  already patched: seperate_audio found in {TARGET}")

if SCROLL_MARKER not in content:
    # Append scroll script before closing ?>
    content = content.rstrip()
    if content.endswith("?>"):
        content = content[:-2].rstrip() + "\n\n" + SCROLL_INJECT + "\n"
    else:
        content += "\n\n" + SCROLL_INJECT + "\n"
    changed = True
else:
    print(f"  already patched: scroll script found in {TARGET}")

if changed:
    with open(TARGET, "w") as f:
        f.write(content)
    print(f"  patched: {TARGET}")
