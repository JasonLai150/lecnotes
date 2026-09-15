# Export final-review fix wave: report

Status: DONE_WITH_CONCERNS (small ones, listed at the end). Suite went from 259 to 291 passed, 0 skipped, no warnings.

## Commits (main, not pushed)

| SHA | Subject | Items |
|---|---|---|
| b38af77 | Reject export -o paths by file identity; protect NOTES.md; clearer export errors | 1, 2, 3, 8, part of 10 (commands.py docstring) |
| 5688b5d | Name Notion zip entries after the link as written; tidy titles; no leftover tmp | 4, 5, 6, 7 |
| ffdd15c | Report wrong-case slide image links in finish as figure_malformed | 9 |
| c5e279a | Update README for export JSON and errors; fix stale fixture comment | 10 |

(6d051bf "Add backlog of deferred work" sits between 57aca23 and my commits. I did not make it.)

## Items

### 1. `invalid_output` bypass
- `src/lecnotes/commands.py:203` new `_same_file(a, b)`, which is `a.exists() and b.exists() and os.path.samefile(a, b)`. It replaces the `resolve()` string comparison at `:248`. The `dest.is_dir()` check is kept.
- `commands.py:268-275`: the brief asked for `dest.parent.exists() and not dest.parent.is_dir()`. I check the **nearest existing ancestor** of `dest` instead, which covers the brief's case and also `-o file/sub/out.html`. Before, that path crashed in `mkdir` with `NotADirectoryError`. See Deviations.
- Tests (`tests/test_export.py`):
  - `test_out_differing_only_in_case_is_rejected[html,notion]` (`:186`). **It ran here and was not skipped**: the macOS tmp filesystem is case-insensitive. Probe: create `a.txt`, check whether `A.TXT` exists.
  - `test_out_linked_to_source_is_rejected[hard,symlink × html,notion]` (`:201`)
  - `test_out_under_a_file_is_rejected[out.html, sub/out.html × html,notion]` (`:219`). This asserts the blocker file is unchanged and nothing new was written.
- RED: the case and hard-link variants failed with `DID NOT RAISE LecnotesError` (for html and notion). Parent-is-a-file failed with `FileExistsError`, and `sub/out.html` with `NotADirectoryError`. The symlink variants passed before the fix because `resolve()` follows symlinks, so they are regression guards. GREEN: all pass.

### 2. `-o <workdir>/NOTES.md`
- `commands.py:157` `_export_source` now returns `(markdown_path, workdir_root_or_None)` (`:192`, `:200`). `commands.py:255` raises `invalid_output` when `dest` is the same file as the workdir's `NOTES.md`.
- Test: `test_out_equal_to_workdir_notes_is_rejected[html,notion]` (`:233`). NOTES.md bytes are unchanged.
- RED: `DID NOT RAISE` for both formats. GREEN: pass.

### 3. `not_finished` wording
- `commands.py:184-191`. The message is now: `NOTES.md and <abs out/<deck>.md> differ. If NOTES.md is the version to keep, run `lecnotes finish` on this workdir first. If out/<deck>.md was edited on purpose, export it directly: `lecnotes export <shell-quoted out path> --to ...``.
- Test: `test_notes_differing_message_offers_both_remedies` (`:243`) asserts the message contains NOTES.md, the out/<deck>.md path, `lecnotes finish` and `lecnotes export`. I added this as a new test. The existing `test_workdir_with_notes_edited_after_finish` still asserts NOTES.md is mentioned and nothing is written.
- RED: assertion failure on the old message, which had no out path. GREEN: pass.

### 4. Notion title sanitizing
- `src/lecnotes/export_notion.py:59` `sanitize_filename` runs these steps in order: collapse `\s+`, drop `unicodedata` category C, `\s*:\s*` → ` - `, `[/\\*?"<>|]` → `-`, strip, cap at `TITLE_MAX`, strip. Regexes are at `:20-22`.
- Tests (`tests/test_export_notion.py`):
  - `test_sanitize_filename` (`:42`): the expected value is now `"B+ Trees - why-how- -fast- -1- - -2-"`, with the step-by-step reasoning in a comment.
  - `test_sanitize_filename_colon_becomes_spaced_dash` (`:120`)
  - `test_sanitize_filename_collapses_whitespace_and_drops_controls` (`:125`): tab, `\x01`, `\x7f`, `\n\n`
  - `test_setext_title_gives_one_line_name` (`:129`): `Learning from Data:\nImitation\n===` → `Learning from Data - Imitation`. Before the fix `split_title` returned `'Learning from Data-\nImitation'`.
- RED: all four failed on assertions. GREEN: pass.

### 5. Zip entry names from `src`
- `src/lecnotes/markdown_doc.py:47` `LocalImage.relpath` = `posixpath.normpath(unquote(src))`. `:52` `mime` now comes from the extension of `unquote(src)`.
- `export_notion.py:90` `images_outside` treats an image as outside when `unquote(src)` is absolute (`os.path.isabs` or leading `/`) or when `relpath` is `..` or starts with `../`. The signature is unchanged.
- `export_notion.py:124-127` `write_notion_zip` stores each image at its `relpath`, reads the bytes from the resolved `image.path`, and de-duplicates by `relpath` in first-seen order.
- Also needed: `src/lecnotes/export_html.py:68` `_data_uri(src, path)` takes its MIME type from the src extension. Without this, a `.png` symlink to a `.bin` file would pass `missing_images` and then `KeyError` in the HTML exporter. See Deviations.
- Tests:
  - `test_symlinked_figure_is_stored_under_its_link_name` (`figures/slide-001.png` → `cache/abc.png`; entry `figures/slide-001.png` with the target's bytes)
  - `test_absolute_src_is_outside_even_when_inside_base_dir`
  - `test_src_that_climbs_back_in_is_still_outside` (`../notes/x.png` is outside, `sub/../x.png` is not)
  - `test_equivalent_srcs_make_one_entry`
  - `test_relpath_is_decoded_and_normalized` and `test_mime_follows_the_src_not_the_symlink_target` (`tests/test_markdown_doc.py:72,77`)
  - `test_symlinked_image_mime_follows_the_src` (`tests/test_export_html.py:97`)
- RED: all failed except `test_equivalent_srcs_make_one_entry`, which already held because the old code de-duplicated by resolved path. It stays as a guard. GREEN: pass.

### 6. No leftover `.tmp`
- `export_notion.py:130-138`: the zip write and `tmp.replace(dest)` are wrapped in `try/except BaseException`, which unlinks the tmp file (`missing_ok=True`) and re-raises.
- Test: `test_failed_zip_write_leaves_no_tmp` (`:171`) monkeypatches `zipfile.ZipFile.write` to raise `OSError`, then asserts that neither `n.zip.tmp` nor `n.zip` exists.
- RED: `n.zip.tmp` existed. GREEN: pass.

### 7. HTML title = first top-level H1
- `export_html.py:100-105` adds `token.level == 0`.
- Test: `test_title_ignores_h1_inside_a_blockquote` (`tests/test_export_html.py:92`): `> # Quoted\n\n# Real\n` → `<title>Real</title>`.
- RED: the title was "Quoted". GREEN: pass.

### 8. `image_not_found` message
- `commands.py:214-229`. The message is `these images cannot be used: missing: a.png, b.png; unsupported type (use png, jpg, jpeg, gif, svg, webp): c.bmp`, and empty groups are left out. The type list comes from `IMAGE_TYPES`. Detail `missing` is unchanged (all offenders, in order). New detail `unsupported` is the subset whose extension is not supported, and may be empty.
- Tests: `test_image_not_found_message_separates_missing_from_unsupported` (`:254`) and `test_image_not_found_message_omits_empty_groups` (`:269`). The existing `test_missing_images_all_listed_nothing_written` is unchanged.
- RED: `KeyError: 'unsupported'`, and the message did not match. GREEN: pass.

### 9. finish: case-insensitive slide shape
- `src/lecnotes/figures.py:84` `SLIDE_PNG_RE` and `:89` `LOOSE_TEXT_RE` are compiled with `re.IGNORECASE`. `STRICT_SRC_RE` stays case-sensitive, with a comment saying why.
- Tests:
  - `test_wrong_case_slide_links_are_malformed_not_refs` (`tests/test_figures_refs.py:148`, 4 cases: `.PNG` image, `SLIDE-` image, `.Png` plain link, `.PNG` in prose)
  - `test_wrong_case_extension_is_malformed` (`tests/test_finish.py:167`): `figure_malformed`, `bad_links == ["figures/slide-002.PNG"]`, no `out/`
- RED: 5 failed; the finish test failed with `DID NOT RAISE`. GREEN: pass.

### 10. Stale wording
- `commands.py:1`: the docstring now reads "Orchestration for prep, finish and export" (in b38af77).
- `README.md:80`: "All three commands take `--json`", with an `export --json` result example next to the prep one.
- `README.md:95-100`: short descriptions of `not_finished`, `image_not_found`, `image_outside_root` and `invalid_output`, plus "Nothing is written when any of them occur."
- `README.md:74-76`: the Export section's "changed since the last finish" sentence now matches the amended not_finished semantics.
- `tests/conftest.py:60`: the comment now reads "slide 8 has 20 line drawings".
- No behavior change, so no RED step. The static error-code guard in `test_cli.py` still passes.

## Full suite

`uv run pytest -rs`: **291 passed in 4.78s**, 0 skipped, no warnings.

## Real-notes sanity check

I copied the three DRL workdirs to `<S>` = `/private/tmp/claude-501/-Users-jasonlai150-Documents-GitHub-4440/b8ce7be5-28b5-4a05-868b-6c0cf5495ca3/scratchpad/drl`. The originals were not touched.

```
$ for w in <S>/*.notes; do lecnotes export $w --to html --json; lecnotes export $w --to notion --json; <list .md entries in zip>; done
== draft-lec-2-cs8803-drl-f26-policy-grad.notes
{"ok": true, "format": "html",   ..., "images": 19, "bytes": 5340817}   exit=0
{"ok": true, "format": "notion", ..., "images": 19, "bytes": 3844490}   exit=0
['Policy Gradients - Optimizing the RL Objective Directly.md'] 19 images
== draft-lec-3-cs8803-drl-f26-actor-critic.notes
{"ok": true, "format": "html",   ..., "images": 10, "bytes": 3296160}   exit=0
{"ok": true, "format": "notion", ..., "images": 10, "bytes": 2363712}   exit=0
['Actor-Critic Algorithms - Taming the Variance of Policy Gradients.md'] 10 images
== lec-1-cs8803-drl-f26-supervised-learning.notes
{"ok": true, "format": "html",   ..., "images": 20, "bytes": 8918673}   exit=0
{"ok": true, "format": "notion", ..., "images": 20, "bytes": 6557307}   exit=0
['Learning from Data - Imitation Learning and Its Limits.md'] 20 images
```

The three Notion entry names:
- `Policy Gradients - Optimizing the RL Objective Directly.md`
- `Actor-Critic Algorithms - Taming the Variance of Policy Gradients.md`
- `Learning from Data - Imitation Learning and Its Limits.md`

Output-safety checks on `<W>` = `<S>/lec-1-cs8803-drl-f26-supervised-learning.notes`:

```
$ snapshot before
0aa992f6...  <W>/NOTES.md
0aa992f6...  <W>/out/lec-1-cs8803-drl-f26-supervised-learning.md
9d380469...  - (listing of out/)
$ lecnotes export <W> --to html -o <W>/NOTES.md --json
{"ok": false, "error": "invalid_output", "message": "exporting to <W>/NOTES.md would overwrite this workdir's NOTES.md; pass a different -o path", "path": "<W>/NOTES.md"}
exit=1
$ lecnotes export <W> --to notion -o <W>/NOTES.md
error: exporting to <W>/NOTES.md would overwrite this workdir's NOTES.md; pass a different -o path
exit=1
$ lecnotes export <W> --to html -o <W>/out/LEC-1-CS8803-DRL-F26-SUPERVISED-LEARNING.MD --json
{"ok": false, "error": "invalid_output", "message": "exporting to <W>/out/LEC-1-CS8803-DRL-F26-SUPERVISED-LEARNING.MD would overwrite the Markdown being exported; pass a different -o path", ...}
exit=1
$ lecnotes export <W>/out/lec-1-cs8803-drl-f26-supervised-learning.md --to notion -o <W>/out/LEC-1-CS8803-DRL-F26-SUPERVISED-LEARNING.MD --json
{"ok": false, "error": "invalid_output", "message": "... would overwrite the Markdown being exported; ...", ...}
exit=1
$ snapshot after
0aa992f6...  <W>/NOTES.md
0aa992f6...  <W>/out/lec-1-cs8803-drl-f26-supervised-learning.md
9d380469...  - (listing of out/, unchanged)
```

New not_finished message on a copy, after appending to `NOTES.md` in `<S>/draft-lec-3-...notes`:

```
error: NOTES.md and <S>/draft-lec-3-cs8803-drl-f26-actor-critic.notes/out/draft-lec-3-cs8803-drl-f26-actor-critic.md differ. If NOTES.md is the version to keep, run `lecnotes finish` on this workdir first. If out/draft-lec-3-cs8803-drl-f26-actor-critic.md was edited on purpose, export it directly: `lecnotes export <S>/draft-lec-3-cs8803-drl-f26-actor-critic.notes/out/draft-lec-3-cs8803-drl-f26-actor-critic.md --to ...`
```

## Deviations and concerns

1. **Parent-is-a-file check (item 1)** looks at the nearest *existing* ancestor, not only `dest.parent`. It is a superset of the brief and matches the amendment ("its parent exists but is not a directory"). It also turns `-o file/sub/out.html` into `invalid_output` instead of a traceback. Both cases are tested.
2. **HTML MIME from src (item 5 follow-on).** The amendment says "An image's MIME type follows the extension in the `src`". The brief only named `LocalImage.mime`, but `export_html._data_uri` used the resolved path's suffix. A `.png` symlink to a `.bin` would then pass validation and crash with `KeyError`, so I changed `_data_uri` to use the src extension too (with a test).
3. **Item 3 test** is a new test rather than an edit of `test_workdir_with_notes_edited_after_finish`. The old test is kept and still asserts NOTES.md is mentioned.
4. **`images` count in the export result** still counts distinct *resolved* paths (`commands.py`, unchanged). In a Notion zip, two different link names that point at one symlink target become two entries but count as 1 image. This is an edge case I left alone because it is outside the brief.
5. **Sanitize order** follows the brief exactly: whitespace is collapsed before control characters are dropped. So `"a \x01 b"` becomes `"a  b"` with two spaces. This is harmless in a file name, but it is not fully normalized.
6. **Symlinked-source `-o` tests** passed before the fix, because the old `resolve()` comparison already followed symlinks. They are kept as regression guards.
