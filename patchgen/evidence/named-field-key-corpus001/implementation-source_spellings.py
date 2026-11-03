"""Bounded source-name decoding; values do not establish receiver identity."""
import re
import unicodedata

HEX = frozenset('0123456789abcdefABCDEF')
ESCAPES = {'0': '\0', 'a': '\a', 'b': '\b', 'f': '\f', 'n': '\n',
           'r': '\r', 't': '\t', 'v': '\v', '\\': '\\', '"': '"', "'": "'"}
UNICODE_ESCAPE = re.compile(r'\\(?:u\{([0-9a-fA-F]+)\}|u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8}))')


def identifier_value(value, language):
    if language == 'python':
        return unicodedata.normalize('NFKC', value)
    if language == 'csharp':
        value = value.removeprefix('@')
    def replace(match):
        # ECMAScript has braced escapes; C# has eight-digit U escapes.
        if match[1] and language != 'typescript' or match[3] and language != 'csharp':
            return match[0]
        try:
            return chr(int(next(part for part in match.groups() if part), 16))
        except ValueError:
            return match[0]
    value = UNICODE_ESCAPE.sub(replace, value)
    if language == 'csharp':
        # C# ignores identifier formatting characters when comparing names.
        value = ''.join(c for c in value if unicodedata.category(c) != 'Cf')
    return value


def quoted_value(value, language):
    """Decode ordinary quoted strings, C# verbatim and static JS templates.

    Interpolations and C# raw/multiline literals are excluded by the caller.
    Invalid escapes return None; never use host-Python escape semantics for JS/C#.
    """
    if language == 'csharp' and value.startswith('@"') and value.endswith('"'):
        return value[2:-1].replace('""', '"')
    delimiters = ('"', "'", '`') if language == 'typescript' else ('"',)
    if len(value) < 2 or value[0] not in delimiters or value[-1] != value[0]:
        return None
    body, out, index = value[1:-1], [], 0
    while index < len(body):
        char = body[index]
        index += 1
        if char != '\\':
            out.append(char)
            continue
        if index == len(body):
            return None
        escape = body[index]
        index += 1
        if language == 'typescript' and escape in '\n\r\u2028\u2029':
            if escape == '\r' and body[index:index+1] == '\n':
                index += 1
            continue
        if escape in ('u', 'U', 'x'):
            if escape == 'u' and language == 'typescript' and body[index:index+1] == '{':
                end = body.find('}', index+1)
                digits = body[index+1:end] if end != -1 else ''
                index = end+1
            else:
                length = {'u': 4, 'U': 8, 'x': 2}[escape]
                if escape == 'U' and language != 'csharp':
                    out.append('U')  # JS NonEscapeCharacter, not a Unicode escape.
                    continue
                if escape == 'x' and language == 'csharp':
                    length = 0
                    while length < 4 and index+length < len(body) and body[index+length] in HEX:
                        length += 1
                digits = body[index:index+length]
                if len(digits) != length:
                    return None
                index += length
            if not digits or any(c not in HEX for c in digits):
                return None
            try:
                out.append(chr(int(digits, 16)))
            except ValueError:
                return None
        elif language == 'typescript' and escape in '01234567':
            # Legacy octal strings can be parsed even when a strict TS build
            # later rejects them. Recognize their value without claiming validity.
            digits = escape
            maximum = 3 if escape in '0123' else 2
            while len(digits) < maximum and index < len(body) and body[index] in '01234567':
                digits += body[index]
                index += 1
            out.append(chr(int(digits, 8)))
        elif escape in ESCAPES and (language == 'csharp' or escape != 'a'):
            out.append(ESCAPES[escape])
        elif language == 'typescript':
            out.append(escape)
        else:
            return None
    return ''.join(out)
