# pip install git+https://github.com/david-why/discord-markdown-ast-parser.git#egg=discord-markdown-ast-parser
import re
from discord_markdown_ast_parser import parse
from discord_markdown_ast_parser.parser import Node, NodeType
from aiogram.types import MessageEntity, LinkPreviewOptions
from aiogram.enums.message_entity_type import MessageEntityType
from typing import Optional
from textwrap import wrap
from limits import TELEGRAM_MESSAGE_LENGTH_LIMIT

TelegramContents = tuple[str, list[MessageEntity], LinkPreviewOptions]

# Discord's markdown to Telegram entities works flawlessly under regular
# circumstances, but *italic with whitespace before star closer *
# will be detected as italic even though the Discord client won't, and
# escaping just won't work. FIXME?

# NOTE: ***text*** is fixed only in this version, apparently

# NOTE: 
# ||spoilers around
# ```
# code blocks
# ```
# || are not supported by Telegram anyway, so there's nothing to fix


def _parse_nodes(offset: int, nodes: list[Node]) -> TelegramContents:
    link_preview_options: LinkPreviewOptions = LinkPreviewOptions()
    text_link_without_preview: bool = False
    
    markdownless_text: str = ""
    entities: list[MessageEntity] = []
    deferred_cursor: int = 0
    
    
    def append(
        results: TelegramContents,
        type: MessageEntityType,
        *,
        url: Optional[str] = None,
        language: Optional[str] = None
    ) -> None:
        nonlocal markdownless_text, entities, deferred_cursor

        deferred_cursor = len(markdownless_text)

        # Handle escaping TODO
        if not re.subn(r"\\(.*)\\?$", r"\1", markdownless_text, flags=re.NOFLAG)[1]:
            entities.append(MessageEntity(
                type=type,
                offset=offset + deferred_cursor,
                length=len(results[0]),
                url=url,
                language=language
            ))
        
        markdownless_text += results[0]
        entities.extend(results[1])
        
    
    for node in nodes:
        if text_link_without_preview: # damn library bugs...
            text_link_without_preview = False
            continue
        
        match node.node_type:
            case NodeType.TEXT if node.text_content:
                markdownless_text += node.text_content
                
            case NodeType.ITALIC if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.ITALIC
                )
                
            case NodeType.BOLD if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.BOLD
                )
                
            case NodeType.UNDERLINE if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.UNDERLINE
                )
                
            case NodeType.STRIKETHROUGH if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.STRIKETHROUGH
                )
            
            case NodeType.SPOILER if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.SPOILER
                )
                
            case NodeType.URL_WITH_PREVIEW if node.url:
                # If the link is not in a markdown...
                if not markdownless_text or markdownless_text[-1] != "(":
                    markdownless_text += node.url
                else:
                    # Remove the parenthesis ( "[.*](" )
                    # Probably an oversight by the developer of the library
                    markdownless_text = \
                        markdownless_text[:deferred_cursor] + \
                        markdownless_text[deferred_cursor + 1:-2]
                        
                    entities.append(MessageEntity(
                        type=MessageEntityType.TEXT_LINK,
                        offset=offset + deferred_cursor,
                        length=len(markdownless_text) - deferred_cursor,
                        url=node.url[:-1] # remove ) from the URL; another oversight
                    ))
                    
                link_preview_options = LinkPreviewOptions(
                    is_disabled=False
                )
            
            case NodeType.URL_WITHOUT_PREVIEW if node.url:
                # If the link is not in a markdown...
                if not markdownless_text or markdownless_text[-1] != "(":
                    markdownless_text += node.url
                else:
                    # Remove the parenthesis ( "[.*](" )
                    # Probably an oversight by the developer of the library
                    markdownless_text = \
                        markdownless_text[:deferred_cursor] + \
                        markdownless_text[deferred_cursor + 1:-2]
                    
                    entities.append(MessageEntity(
                        type=MessageEntityType.TEXT_LINK,
                        offset=offset + deferred_cursor,
                        length=len(markdownless_text) - deferred_cursor,
                        url=node.url # here the oversight is moved
                    ))
                    
                    text_link_without_preview = True # remove ) from the URL next iteration
                
                link_preview_options = LinkPreviewOptions(
                    is_disabled=True
                )
                
            case NodeType.QUOTE_BLOCK if node.children:
                append(
                    results=_parse_nodes(
                        offset=offset + len(markdownless_text),
                        nodes=node.children
                    ),
                    type=MessageEntityType.BLOCKQUOTE
                )
            
            case NodeType.CODE_INLINE if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.CODE
                )
            
            case NodeType.CODE_BLOCK if node.children:
                append(
                    results=_parse_nodes(offset, node.children),
                    type=MessageEntityType.PRE,
                    language=node.code_lang
                )

    return markdownless_text, entities, link_preview_options


def parse_markdown(offset: int, text: str) -> TelegramContents:
    return _parse_nodes(offset, parse(text[offset:]))


def get_entities_wrapped(
    suffix: str,
    text: str
) -> tuple[list[str], list[list[MessageEntity]], LinkPreviewOptions]:
    wrapped_text: list[str] = []
    entities: list[list[MessageEntity]] = []
    link_preview_options: LinkPreviewOptions = LinkPreviewOptions()
    
    for i, content in enumerate(
        iterable=wrap(
            suffix + text,
            TELEGRAM_MESSAGE_LENGTH_LIMIT,
            break_long_words=False,
            replace_whitespace=False
        ),
        start=0
    ):
        results: TelegramContents = parse_markdown(
            offset=len(suffix) if i == 0 else 0,
            text=content
        )
        
        wrapped_text.append((suffix + results[0]) if i == 0 else results[0])
        entities.append(results[1])
        link_preview_options = results[2]

    return wrapped_text, entities, link_preview_options
