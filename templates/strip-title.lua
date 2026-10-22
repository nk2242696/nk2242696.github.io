-- Normalizes Word-authored post bodies before the template renders them.
-- The template owns the title and article metadata, while Word documents may
-- repeat those values as their first few paragraphs. Word also commonly emits
-- visual section headings as bold-only paragraphs instead of semantic headers.

local function text_of(block)
  return pandoc.utils.stringify(block):gsub("^%s+", ""):gsub("%s+$", "")
end

local function is_strong_only(block)
  return block.t == "Para"
    and #block.content == 1
    and block.content[1].t == "Strong"
end

local function is_emph_only(block)
  return block.t == "Para"
    and #block.content == 1
    and block.content[1].t == "Emph"
end

local function section_id(text, used_ids)
  local id = text:lower()
    :gsub("[^a-z0-9%s-]", "")
    :gsub("[%s_]+", "-")
    :gsub("%-+", "-")
    :gsub("^%-", "")
    :gsub("%-$", "")

  if id == "" then
    id = "section"
  end

  local candidate = id
  local suffix = 2
  while used_ids[candidate] do
    candidate = id .. "-" .. suffix
    suffix = suffix + 1
  end
  used_ids[candidate] = true
  return candidate
end

function Image(image)
  image.attributes.width = nil
  image.attributes.height = nil
  image.attributes.loading = "lazy"
  image.attributes.decoding = "async"
  return image
end

function Para(block)
  if #block.content == 1 and block.content[1].t == "Image" then
    return pandoc.Div({ block }, pandoc.Attr("", { "article-figure" }))
  end
end

local function is_intro_text(block)
  if block.t == "Para" then
    return true
  end
  return block.t == "Div" and block.classes:includes("article-lead")
end

function Pandoc(doc)
  local title = text_of(doc.meta.title)
  local cleaned = pandoc.List()
  local lead_seen = false
  local used_ids = {}

  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" and block.identifier ~= "" then
      used_ids[block.identifier] = true
    end
  end

  for index, block in ipairs(doc.blocks) do
    -- Top-level Plain blocks would become anonymous items in the article grid.
    if block.t == "Plain" then
      block = pandoc.Para(block.content)
      block = Para(block) or block
    end
    local text = text_of(block)
    local in_intro = index <= 6
    local duplicate_title = in_intro
      and text == title
      and (is_strong_only(block) or (block.t == "Header" and block.level == 1))
    local duplicate_date = in_intro and text:match("^%d%d%d%d%-%d%d%-%d%d%s+·%s+%d+%s+min read$")
    local duplicate_tags = in_intro and is_emph_only(block) and text:find("·", 1, true)

    if not duplicate_title and not duplicate_date and not duplicate_tags then
      if is_strong_only(block) and not lead_seen then
        -- Keep the first bold-only paragraph as the article's standfirst.
        lead_seen = true
        cleaned:insert(pandoc.Div({ block }, pandoc.Attr("", { "article-lead" })))
      elseif is_strong_only(block) then
        local id = section_id(text, used_ids)
        cleaned:insert(pandoc.Header(2, block.content[1].content, pandoc.Attr(id)))
      else
        cleaned:insert(block)
      end
    end
  end

  local intro = pandoc.List()
  while #cleaned > 0 and #intro < 3 and is_intro_text(cleaned[1]) do
    intro:insert(cleaned:remove(1))
  end
  if #intro > 0 then
    doc.meta["article-intro"] = pandoc.MetaBlocks(intro)
  end

  doc.blocks = cleaned
  return doc
end
