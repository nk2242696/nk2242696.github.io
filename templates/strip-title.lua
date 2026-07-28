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
    :gsub("[^%w%s-]", "")
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
    local text = text_of(block)
    local in_intro = index <= 6
    local duplicate_title = in_intro and is_strong_only(block) and text == title
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

  doc.blocks = cleaned
  return doc
end
