from aiogram.types import MessageEntity
from aiogram.enums.message_entity_type import MessageEntityType
from discord.utils import escape_markdown
from typing import Optional


def parse_markdown(
    original_text: str,
    entities: Optional[list[MessageEntity]],
    disable_link_preview: bool = False
) -> str:
    if not entities:
        return escape_markdown(original_text, ignore_links=False)
    
    markdown_text: str = ""
    cursor: int = 0 # Always moved to the end of each entity
    blockquote_end: int = 0
    
    for entity in entities:
        entity_end: int = entity.offset + entity.length
        
        text_slice: str = ""
        if cursor >= blockquote_end: # Not inside a blockquote
            text_slice += original_text[cursor:entity.offset]
        else:
            text_slice = original_text[
                cursor:(
                    entity.offset
                    if entity.offset < blockquote_end # Next entity starts inside blockquote
                    else blockquote_end # Include all inside the blockquote
                )
            ].replace('\n', "\n> ")
            text_slice += original_text[blockquote_end:entity.offset]
        
        text_slice = escape_markdown(text_slice, ignore_links=False)
        entity_text: str = original_text[entity.offset:entity_end]

        match entity.type:
            case MessageEntityType.BOLD:
                text_slice += f"**{entity_text}**"
            
            case MessageEntityType.ITALIC:
                text_slice += f"_{entity_text}_"
                
            case MessageEntityType.UNDERLINE:
                text_slice += f"__{entity_text}__"
                
            case MessageEntityType.STRIKETHROUGH:
                text_slice += f"~~{entity_text}~~"
                
            case MessageEntityType.SPOILER:
                text_slice += f"||{entity_text}||"
                
            case MessageEntityType.CODE:
                text_slice += f"`{entity_text}`"
            
            case MessageEntityType.PRE:
                text_slice += f"```{entity.language}\n{entity_text}```"
                
            case MessageEntityType.TEXT_LINK:
                print(disable_link_preview)
                text_slice += (
                    f"[{entity_text}](<{entity.url}>)"
                    if disable_link_preview
                    else f"[{entity_text}]({entity.url})"
                )
            
            case MessageEntityType.BLOCKQUOTE | \
            MessageEntityType.EXPANDABLE_BLOCKQUOTE:
                markdown_text += f"{text_slice}> "
                
                blockquote_end = entity_end
                cursor = entity.offset
                continue
            case _:
                text_slice += entity_text

        markdown_text += text_slice
        cursor = entity.offset + entity.length
    else:
        if blockquote_end:
            markdown_text += original_text[cursor:blockquote_end].replace('\n', "\n> ")
            cursor = blockquote_end
        
        return markdown_text + original_text[cursor:]
