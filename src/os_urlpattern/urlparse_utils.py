import StringIO
import hashlib
from urlparse import urlparse, ParseResult
from definition import QUERY_PART_RESERVED_CHARS, EMPTY_LIST, BLANK_LIST
from definition import ASCII_DIGIT_SET, CHAR_RULE_DICT, SIGN_RULE_SET


class IrregularURLException(Exception):
    pass


class URLMeta(object):
    __slots__ = ['_path_depth', '_query_keys', '_has_fragment', '_hashcode']

    def __init__(self, path_depth, query_keys, has_fragment):
        self._path_depth = path_depth
        self._query_keys = query_keys
        self._has_fragment = has_fragment
        self._hashcode = None

    def __hash__(self):
        return hash(self.hashcode)

    def __eq__(self, o):
        return hash(o) == hash(self)

    @property
    def hashcode(self):
        if self._hashcode is None:
            s = StringIO.StringIO()
            s.write(self._path_depth)
            if self._query_keys:
                s.write('?')
                s.write('&'.join(self._query_keys))
            if self._has_fragment:
                s.write('#')
            s.seek(0)
            self._hashcode = hashlib.md5(s.read()).hexdigest()
        return self._hashcode

    @property
    def depths(self):
        return (self.path_depth, self.query_depth, self.fragment_depth)

    @property
    def query_keys(self):
        return self._query_keys

    @property
    def query_depth(self):
        return len(self._query_keys)

    @property
    def fragment_depth(self):
        return 1 if self._has_fragment else 0

    @property
    def path_depth(self):
        return self._path_depth

    @property
    def has_fragment(self):
        return self._has_fragment

    @property
    def depth(self):
        return sum((self.path_depth, self.query_depth, self.fragment_depth))


def _exact_num(rule, num):
    if num == 1:
        return '[%s]' % rule
    return '[%s]{%d}' % (rule, num)


def normalize_str_list(str_list, reserved_chars):
    return [normalize_str(i, reserved_chars) for i in str_list]


def normalize_str(raw_string, reserved_chars=None):
    normal_str = StringIO.StringIO()
    frag = StringIO.StringIO()
    last_c = None
    for c in raw_string:
        if c in ASCII_DIGIT_SET:
            if last_c and last_c not in ASCII_DIGIT_SET:
                frag.seek(0)
                w = frag.read()
                l = len(w)
                if l > 0:
                    if not reserved_chars or w[0] not in reserved_chars:
                        r = CHAR_RULE_DICT.get(w[0])
                        w = _exact_num(r, l)
                    normal_str.write(w)
                    frag = StringIO.StringIO()
        else:
            if last_c != c:
                frag.seek(0)
                w = frag.read()
                l = len(w)
                if l > 0 and w[0] not in ASCII_DIGIT_SET and \
                        (not reserved_chars or w[0] not in reserved_chars):
                    r = CHAR_RULE_DICT.get(w[0])
                    w = _exact_num(r, l)
                normal_str.write(w)
                frag = StringIO.StringIO()
        frag.write(c)
        last_c = c

    frag.seek(0)
    w = frag.read()
    l = len(w)
    if last_c and last_c not in ASCII_DIGIT_SET and \
            (not reserved_chars or w[0] not in reserved_chars):
        r = CHAR_RULE_DICT.get(w[0])
        w = _exact_num(r, l)
    normal_str.write(w)
    normal_str.seek(0)
    return normal_str.read()


def analyze_url(url):
    scheme, netloc, path, params, query, fragment = urlparse(url)
    if not fragment:
        if url[-1] != '#':
            fragment = None
            if not query and url[-1] != '?':
                query = None
        elif not query and url[-2] != '?':
            query = None
    elif not query:
        if url[len(url) - len(fragment) - 2] != '?':
            query = None
    return ParseResult(scheme, netloc, path, params, query, fragment)


def filter_useless_part(parts):
    keep = {'c': 0, 'l': len(parts)}

    def _filterd(x):
        keep['c'] += 1
        if not x:
            if keep['c'] == keep['l']:
                return True
            return False
        else:
            return True

    return filter(_filterd, parts)


def parse_query_string(query_string):
    if query_string is None:
        return EMPTY_LIST, EMPTY_LIST
    elif query_string == '':
        return BLANK_LIST, BLANK_LIST
    elif query_string.endswith('&'):
        raise IrregularURLException('Invalid url query')
    kv_type = True  # qkey True, qvalue False
    last_c = None
    kv_buf = {True: StringIO.StringIO(), False: StringIO.StringIO()}
    kv_list = {True: [], False: []}
    for i in query_string:
        if i == '=' and kv_type:
            s = kv_buf[kv_type]
            s.write(i)
            s.seek(0)
            kv_list[kv_type].append(s.read())
            kv_buf[kv_type] = StringIO.StringIO()
            kv_type = not kv_type
        elif i == '&':
            if last_c is None or last_c == '&':
                raise IrregularURLException('Invalid url query')
            s = kv_buf[kv_type]
            s.seek(0)
            kv_list[kv_type].append(s.read())
            kv_buf[kv_type] = StringIO.StringIO()
            if kv_type:
                kv_list[False].append('')  # treat as value-less
            else:
                kv_type = not kv_type
        else:
            s = kv_buf[kv_type]
            s.write(i)
        last_c = i

    s = kv_buf[kv_type]
    s.seek(0)
    kv_list[kv_type].append(s.read())
    if kv_type:  # treat as value-less
        kv_list[False].append('')

    # only one query without value, treat as key-less
    if len(kv_list[True]) == 1 and not kv_list[True][0].endswith('='):
        kv_list[False][0], kv_list[True][0] = kv_list[True][0], kv_list[False][0]
    return kv_list[True], kv_list[False]


def unpack(result, norm_query_key=True):
    pieces = filter_useless_part(result.path.split('/')[1:])
    path_depth = len(pieces)
    assert path_depth > 0

    key_list, value_list = parse_query_string(result.query)
    if norm_query_key:
        key_list = normalize_str_list(key_list, QUERY_PART_RESERVED_CHARS)
    has_fragment = False if result.fragment is None else True

    url_meta = URLMeta(path_depth, key_list, has_fragment)
    pieces.extend(value_list)
    if has_fragment:
        pieces.append(result.fragment)
    return url_meta, pieces


def pack(url_meta, paths):
    s = StringIO.StringIO()
    s.write('/')
    idx = url_meta.path_depth + url_meta.query_depth
    p = '/'.join([str(p) for p in paths[0:url_meta.path_depth]])
    s.write(p)
    if url_meta.query_depth > 0:
        s.write('[\\?]')
        kv = zip(url_meta.query_keys,
                 [str(p) for p in paths[url_meta.path_depth:idx]])
        s.write('&'.join([''.join((str(k), str(v))) for k, v in kv]))

    if url_meta.has_fragment:
        s.write('#')
        s.write(''.join([str(p) for p in paths[idx:]]))
    s.seek(0)
    return s.read()


def parse_url(url):
    result = analyze_url(url)
    return unpack(result, True)


class ParsedPiece(object):
    __slots__ = ['_pieces', '_rules', '_piece', '_piece_length', '_fuzzy_rule']

    def __init__(self, pieces, rules):
        self._pieces = pieces
        self._rules = rules
        self._piece = None
        self._piece_length = -1
        self._fuzzy_rule = None

    @property
    def fuzzy_rule(self):
        if not self._fuzzy_rule:
            self._fuzzy_rule = ''.join(sorted(set(self.rules)))
        return self._fuzzy_rule

    @property
    def rules(self):
        return self._rules

    @property
    def pieces(self):
        return self._pieces

    @property
    def piece_length(self):
        if self._piece_length < 0:
            length_base = length = len(self.piece)
            idx = 0
            while idx < length_base:
                c = self.piece[idx]
                if c == '[' or c == ']':
                    if idx == 0 or self.piece[idx - 1] != '\\':
                        length += -1
                elif c == '\\':
                    if self.piece[idx + 1] != '\\':
                        length += -1
                elif c == '{':
                    if self.piece[idx - 1] == ']':
                        e = self.piece.index('}', idx)
                        length += int(self.piece[idx + 1:e]
                                      ) - 1 - (e - idx + 1)
                        idx = e
                idx += 1

            self._piece_length = length
        return self._piece_length

    def __eq__(self, o):
        if not isinstance(o, ParsedPiece):
            return False
        return self.piece == o.piece

    @property
    def piece(self):
        if self._piece is None:
            self._piece = ''.join(self._pieces)
        return self._piece

    def __str__(self):
        return str(zip(self.pieces, self.rules))

    __repr__ = __str__


EMPTY_PARSED_PIECE = ParsedPiece([], [])


class PieceParser(object):
    def __init__(self):
        self._cache = {}
        self._rule_list = None
        self._piece_list = None
        self._reset()

    def _reset(self):
        self._rule_list = []
        self._piece_list = []

    def parse(self, piece):
        if piece not in self._cache:
            self._reset()
            self._pre_process(piece)
            self._cache[piece] = self._create_parsed_piece()
        return self._cache[piece]

    def _pre_process(self, piece):
        for c in piece:
            self._define(c)
        for idx, buf in enumerate(self._piece_list):
            buf.seek(0)
            letter = buf.read()
            self._piece_list[idx] = self._normalize(
                letter, self._rule_list[idx])

    def _define(self, char):
        last_rule = self._rule_list[-1] if self._rule_list else None
        rule = CHAR_RULE_DICT[char]

        if last_rule != rule:
            self._piece_list.append(StringIO.StringIO())
            self._rule_list.append(rule)
        self._piece_list[-1].write(char)

    def _normalize(self, letter, rule):
        if rule in SIGN_RULE_SET:
            return _exact_num(rule, len(letter))
        return letter

    def _create_parsed_piece(self):
        piece_rule = ParsedPiece(self._piece_list, self._rule_list)
        return piece_rule


def struct_id(url_meta, parsed_pieces):
    meta_hash = url_meta.hashcode
    pieces_hash = hashlib.md5(
        '/'.join([p.fuzzy_rule for p in parsed_pieces])).hexdigest()
    return '-'.join((meta_hash, pieces_hash))
