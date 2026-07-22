-- Removes the document's first level-1 heading from the body.
-- The post title is rendered from metadata (sidecar .meta.yaml or filename) in
-- the HTML template, so a title typed as "Heading 1" in Word would otherwise
-- appear twice. This drops only the first H1; all other headings are untouched.

local removed = false

function Header(el)
  if not removed and el.level == 1 then
    removed = true
    return {}
  end
  return nil
end
