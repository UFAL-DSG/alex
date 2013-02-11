#!/usr/bin/env python
# -*- coding: utf-8 -*-


def split_by_comma(text):
    parentheses = 0
    splitList = []

    oldI = 0
    for i in range(len(text)):
        if text[i] == '(':
            parentheses += 1
        elif text[i] == ')':
            parentheses -= 1
            if parentheses < 0:
                raise ValueError("Missing a left parenthesis.")
        elif text[i] == ',':
            if parentheses == 0:
                if oldI == i:
                    raise ValueError(
                        "Spited segment do not have to start with a comma.")
                else:
                    splitList.append(text[oldI:i].strip())
                    oldI = i + 1
    else:
        splitList.append(text[oldI:].strip())

    return splitList


def split_by(text, splitter,
             opening_parentheses='',
             closing_parentheses='',
             quotes="'\""):
    """Splits the input text at each occurrence of the splitter only if it is
    not enclosed in parentheses.

    text - the input text string
    splitter - multi-character string which is used to determine the position
               of splitting of the text
    opening_parentheses - an iterable of opening parentheses that has to be
                          respected when splitting, e.g. "{(" (default: '')
    closing_parentheses - an iterable of closing parentheses that has to be
                          respected when splitting, e.g. "})" (default: '')
    quotes - an iterable of quotes that have to come in pairs, e.g. '"'

    """
    split_list = []

    # Interpret the arguments.
    parentheses_counter = dict((char, 0)
                               for char in opening_parentheses + quotes)
    map_closing_to_opening = dict(zip(closing_parentheses,
                                      opening_parentheses))

    segment_start = 0
    segment_end = 0
    while segment_end < len(text):
        cur_char = text[segment_end]
        if cur_char in opening_parentheses:
            parentheses_counter[cur_char] += 1
        elif cur_char in closing_parentheses:
            parentheses_counter[map_closing_to_opening[cur_char]] -= 1

            if parentheses_counter[map_closing_to_opening[cur_char]] < 0:
                raise ValueError(("Missing an opening parenthesis for: {par} "
                                  "in the text: {text}").format(par=cur_char,
                                                                text=text))
        elif cur_char in quotes:
            parentheses_counter[cur_char] = (
                parentheses_counter[cur_char] + 1) % 2
        elif text[segment_end:].startswith(splitter):
            # Test that all parentheses are closed.
            if all([count == 0 for count in parentheses_counter.values()]):
                split_list.append(text[segment_start:segment_end].strip())
                segment_end += len(splitter)
                segment_start = segment_end

        segment_end += 1
    else:
        split_list.append(text[segment_start:segment_end].strip())

    return split_list


def parse_command(command):
    """Parse the command name(var1="val1",...) into a dictionary strucure:

      E.g. call(destination="1245",opt="X") will be parsed into:

        { "__name__":    "call",
          "destination": "1245",
          "opt":         "X"}

      Return the parsed command in a dictionary.
    """

    try:
        i = command.index('(')
    except ValueError:
        raise Exception(
            "Parsing error in: %s. Missing opening parenthesis." % command)

    name = command[:i]
    d = {"__name__": name}

    # remove the parentheses
    command_svs = command[i + 1:len(command) - 1]

    if not command_svs:
        # there are no parameters
        return d

    command_svs = split_by(command_svs, ',', '', '', '"')

    for command_sv in command_svs:
        i = split_by(command_sv, '=', '', '', '"')
        if len(i) == 1:
            raise Exception("Parsing error in: %s: %s. There is only variable name" % (command, str(i)))
        elif len(i) == 2:
            # there is slot name and value
            d[i[0]] = i[1][1:-1]
        else:
            raise Exception("Parsing error in: %s: %s" % (command, str(i)))

    return d


def escape_special_characters_shell(text, characters="'\""):
    for character in characters:
        text = text.replace(character, '\\' + character)
    return text
