# -*- coding: utf-8 -*-
"""

    Copyright (C) 2012-2021 https://github.com/pytube/pytube/
    SPDX-License-Identifier: Unlicense

    Copyright (C) 2021 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
from copy import copy

from ....kodion import logger


class CalculateN:
    def __init__(self, js):
        raw_code = get_throttling_function_code(js)
        self.throttling_plan = get_throttling_plan(raw_code)
        self.throttling_array = get_throttling_function_array(raw_code)

        self.calculated_n = None

    def calculate_n(self, initial_n):
        """Converts n to the correct value to prevent throttling."""
        if self.calculated_n:
            logger.log_debug('`n` already calculated: {calculated_n}. returning early...'
                             .format(calculated_n=self.calculated_n))
            return self.calculated_n

        if not self.throttling_plan or not self.throttling_array:
            return ''

        logger.log_debug('Attempting to calculate `n` from initial: {initial_n}'
                         .format(initial_n=''.join(initial_n)))

        # First, update all instances of 'b' with the list(initial_n)
        for i in range(len(self.throttling_array)):
            if self.throttling_array[i] == 'b':
                self.throttling_array[i] = initial_n

        for step in self.throttling_plan:
            curr_func = self.throttling_array[int(step[0])]
            if not callable(curr_func):
                logger.log_debug('{curr_func} is not callable.'.format(curr_func=curr_func))
                logger.log_debug('Throttling array:\n{throttling_array}\n'
                                 .format(throttling_array=self.throttling_array))
                return None
            first_arg = self.throttling_array[int(step[1])]

            if len(step) == 2:
                curr_func(first_arg)
            elif len(step) == 3:
                second_arg = self.throttling_array[int(step[2])]
                curr_func(first_arg, second_arg)

        self.calculated_n = ''.join(initial_n)
        logger.log_debug('Calculated `n`: {calculated_n}'
                         .format(calculated_n=self.calculated_n))
        return self.calculated_n


def find_object_from_startpoint(html, start_point):
    """Parses input html to find the end of a JavaScript object.
    :param str html:
        HTML to be parsed for an object.
    :param int start_point:
        Index of where the object starts.
    :rtype dict:
    :returns:
        A dict created from parsing the object.
    """
    html = html[start_point:]
    if html[0] not in ['{', '[']:
        logger.log_debug('Invalid start point. Start of HTML:\n{html_start}'
                         .format(html_start=html[:20]))
        return ''

    # First letter MUST be a open brace, so we put that in the stack,
    # and skip the first character.
    stack = [html[0]]
    i = 1

    context_closers = {
        '{': '}',
        '[': ']',
        '"': '"'
    }

    while i < len(html):
        if len(stack) == 0:
            break
        curr_char = html[i]
        curr_context = stack[-1]

        # If we've reached a context closer, we can remove an element off the stack
        if curr_char == context_closers[curr_context]:
            stack.pop()
            i += 1
            continue

        # Strings require special context handling because they can contain
        #  context openers *and* closers
        if curr_context == '"':
            # If there's a backslash in a string, we skip a character
            if curr_char == '\\':
                i += 2
                continue
        else:
            # Non-string contexts are when we need to look for context openers.
            if curr_char in context_closers.keys():
                stack.append(curr_char)

        i += 1

    full_obj = html[:i]
    return full_obj  # noqa: R504


def get_throttling_function_name(js):
    """Extract the name of the function that computes the throttling parameter.
    :param str js:
        The contents of the base.js asset file.
    :rtype
    :returns:
        The name of the function used to compute the throttling parameter.
    """
    function_patterns = [
        # https://github.com/ytdl-org/youtube-dl/issues/29326#issuecomment-865985377
        # a.C&&(b=a.get("n"))&&(b=Dea(b),a.set("n",b))}};
        # In above case, `Dea` is the relevant function name
        r'a\.C&&\(b=a\.get\("n"\)\)&&\(b=([^(]+)\(b\),a\.set\("n",b\)\)}};',
    ]
    logger.log_debug('Finding throttling function name')
    for pattern in function_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(js)
        if function_match:
            logger.log_debug("finished regex search, matched: %s" % pattern)
            return function_match.group(1)

    return ''


def get_throttling_function_code(js):
    """Extract the raw code for the throttling function.
    :param str js:
        The contents of the base.js asset file.
    :rtype
    :returns:
        The name of the function used to compute the throttling parameter.
    """
    # Begin by extracting the correct function name
    name = re.escape(get_throttling_function_name(js))
    if not name:
        return ''

    # Identify where the function is defined
    pattern_start = r"%s=function\(\w\)" % name
    regex = re.compile(pattern_start)
    match = regex.search(js)
    if not match:
        return ''

    # Extract the code within curly braces for the function itself, and merge any split lines
    code_lines_list = find_object_from_startpoint(js, match.span()[1]).split('\n')
    if not code_lines_list:
        return ''

    joined_lines = "".join(code_lines_list)

    # Prepend function definition (e.g. `Dea=function(a)`)
    return match.group(0) + joined_lines


def get_throttling_function_array(raw_code):
    """Extract the "c" array.
    :param str raw_code:
        The response from get_throttling_function_code(js).
    :returns:
        The array of various integers, arrays, and functions.
    """

    array_start = r",c=\["
    array_regex = re.compile(array_start)
    match = array_regex.search(raw_code)
    if not match:
        return []

    array_raw = find_object_from_startpoint(raw_code, match.span()[1] - 1)
    str_array = throttling_array_split(array_raw)

    converted_array = []
    for el in str_array:
        try:
            converted_array.append(int(el))
            continue
        except ValueError:
            # Not an integer value.
            pass

        if el == 'null':
            converted_array.append(None)
            continue

        if el.startswith('"') and el.endswith('"'):
            # Convert e.g. '"abcdef"' to string without quotation marks, 'abcdef'
            converted_array.append(el[1:-1])
            continue

        if el.startswith('function'):
            mapper = (
                (r"{for\(\w=\(\w%\w\.length\+\w\.length\)%\w\.length;\w--;\)\w\.unshift\(\w.pop\(\)\)}", throttling_unshift),  # noqa:E501
                (r"{\w\.reverse\(\)}", throttling_reverse),
                (r"{\w\.push\(\w\)}", throttling_push),
                (r";var\s\w=\w\[0\];\w\[0\]=\w\[\w\];\w\[\w\]=\w}", throttling_swap),
                (r"case\s\d+", throttling_cipher_function),
                (r"\w\.splice\(0,1,\w\.splice\(\w,1,\w\[0\]\)\[0\]\)", throttling_nested_splice),  # noqa:E501
                (r";\w\.splice\(\w,1\)}", js_splice),
                (r"\w\.splice\(-\w\)\.reverse\(\)\.forEach\(function\(\w\){\w\.unshift\(\w\)}\)", throttling_prepend),  # noqa:E501
                (r"for\(var \w=\w\.length;\w;\)\w\.push\(\w\.splice\(--\w,1\)\[0\]\)}", throttling_reverse),  # noqa:E501
            )

            found = False
            for pattern, fn in mapper:
                if re.search(pattern, el):
                    converted_array.append(fn)
                    found = True
            if found:
                continue

        converted_array.append(el)

    # Replace null elements with array itself
    for i in range(len(converted_array)):
        if converted_array[i] is None:
            converted_array[i] = converted_array

    return converted_array


def get_throttling_plan(raw_code):
    """Extract the "throttling plan".
    The "throttling plan" is a list of tuples used for calling functions
    in the c array. The first element of the tuple is the index of the
    function to call, and any remaining elements of the tuple are arguments
    to pass to that function.
    :param str raw_code:
        The response from get_throttling_function_code(js).
    :returns:
        The full function code for computing the throttling parameter.
    """

    transform_start = r"try{"
    plan_regex = re.compile(transform_start)
    match = plan_regex.search(raw_code)
    if not match:
        return []

    transform_plan_raw = find_object_from_startpoint(raw_code, match.span()[1] - 1)

    # Steps are either c[x](c[y]) or c[x](c[y],c[z])
    step_start = r"c\[(\d+)\]\(c\[(\d+)\](,c(\[(\d+)\]))?\)"
    step_regex = re.compile(step_start)
    matches = step_regex.findall(transform_plan_raw)
    transform_steps = []
    for match in matches:
        if match[4] != '':
            transform_steps.append((match[0], match[1], match[4]))
        else:
            transform_steps.append((match[0], match[1]))

    return transform_steps


def throttling_reverse(arr):
    """Reverses the input list.
    Needs to do an in-place reversal so that the passed list gets changed.
    To accomplish this, we create a reversed copy, and then change each
    indvidual element.
    """
    reverse_copy = copy(arr)[::-1]
    for i in range(len(reverse_copy)):
        arr[i] = reverse_copy[i]


def throttling_push(d, e):
    """Pushes an element onto a list."""
    d.append(e)


def throttling_mod_func(d, e):
    """Perform the modular function from the throttling array functions.
    In the javascript, the modular operation is as follows:
    e = (e % d.length + d.length) % d.length
    We simply translate this to python here.
    """
    return (e % len(d) + len(d)) % len(d)


def throttling_unshift(d, e):
    """Rotates the elements of the list to the right.
    In the javascript, the operation is as follows:
    for(e=(e%d.length+d.length)%d.length;e--;)d.unshift(d.pop())
    """
    e = throttling_mod_func(d, e)
    new_arr = d[-e:] + d[:-e]
    del d[:]
    for el in new_arr:
        d.append(el)


def throttling_cipher_function(d, e):
    """This ciphers d with e to generate a new list.
    In the javascript, the operation is as follows:
    var h = [A-Za-z0-9-_], f = 96;  // simplified from switch-case loop
    d.forEach(
        function(l,m,n){
            this.push(
                n[m]=h[
                    (h.indexOf(l)-h.indexOf(this[m])+m-32+f--)%h.length
                ]
            )
        },
        e.split("")
    )
    """
    h = list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
    f = 96
    # by naming it "this" we can more closely reflect the js
    this = list(e)

    # This is so we don't run into weirdness with enumerate while
    #  we change the input list
    copied_list = copy(d)

    for m, l in enumerate(copied_list):
        bracket_val = (h.index(l) - h.index(this[m]) + m - 32 + f) % len(h)
        this.append(
            h[bracket_val]
        )
        d[m] = h[bracket_val]
        f -= 1


def throttling_nested_splice(d, e):
    """Nested splice function in throttling js.
    In the javascript, the operation is as follows:
    function(d,e){
        e=(e%d.length+d.length)%d.length;
        d.splice(
            0,
            1,
            d.splice(
                e,
                1,
                d[0]
            )[0]
        )
    }
    While testing, all this seemed to do is swap element 0 and e,
    but the actual process is preserved in case there was an edge
    case that was not considered.
    """
    e = throttling_mod_func(d, e)
    inner_splice = js_splice(
        d,
        e,
        1,
        d[0]
    )
    js_splice(
        d,
        0,
        1,
        inner_splice[0]
    )


def throttling_prepend(d, e):
    """
    In the javascript, the operation is as follows:
    function(d,e){
        e=(e%d.length+d.length)%d.length;
        d.splice(-e).reverse().forEach(
            function(f){
                d.unshift(f)
            }
        )
    }
    Effectively, this moves the last e elements of d to the beginning.
    """
    start_len = len(d)
    # First, calculate e
    e = throttling_mod_func(d, e)

    # Then do the prepending
    new_arr = d[-e:] + d[:-e]

    # And update the input list
    del d[:]
    for el in new_arr:
        d.append(el)

    end_len = len(d)
    assert start_len == end_len


def throttling_swap(d, e):
    """Swap positions of the 0'th and e'th elements in-place."""
    e = throttling_mod_func(d, e)
    f = d[0]
    d[0] = d[e]
    d[e] = f


def js_splice(arr, start, delete_count=None, *items):
    """Implementation of javascript's splice function.
    :param list arr:
        Array to splice
    :param int start:
        Index at which to start changing the array
    :param int delete_count:
        Number of elements to delete from the array
    :param *items:
        Items to add to the array
    Reference: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/splice  # noqa:E501
    """
    # Special conditions for start value
    try:
        if start > len(arr):
            start = len(arr)
        # If start is negative, count backwards from end
        if start < 0:
            start = len(arr) - start
    except TypeError:
        # Non-integer start values are treated as 0 in js
        start = 0

    # Special condition when delete_count is greater than remaining elements
    if not delete_count or delete_count >= len(arr) - start:
        delete_count = len(arr) - start  # noqa: N806

    deleted_elements = arr[start:start + delete_count]

    # Splice appropriately.
    new_arr = arr[:start] + list(items) + arr[start + delete_count:]

    # Replace contents of input array
    del arr[:]
    for el in new_arr:
        arr.append(el)

    return deleted_elements


def throttling_array_split(js_array):
    """Parses the throttling array into a python list of strings.
    Expects input to begin with `[` and close with `]`.
    :param str js_array:
        The javascript array, as a string.
    :rtype:
    :returns:
        A list of strings representing splits on `,` in the throttling array.
    """
    results = []
    curr_substring = js_array[1:]

    comma_regex = re.compile(r",")
    func_regex = re.compile(r"function\([^)]+\)")

    while len(curr_substring) > 0:
        if curr_substring.startswith('function'):
            # Handle functions separately. These can contain commas
            match = func_regex.search(curr_substring)
            if not match:
                return []

            match_start, match_end = match.span()

            function_text = find_object_from_startpoint(curr_substring, match.span()[1])
            full_function_def = curr_substring[:match_end + len(function_text)]
            results.append(full_function_def)
            curr_substring = curr_substring[len(full_function_def) + 1:]
        else:
            match = comma_regex.search(curr_substring)
            if not match:
                return []

            # Try-catch to capture end of array
            try:
                match_start, match_end = match.span()
            except AttributeError:
                match_start = len(curr_substring) - 1
                match_end = match_start + 1

            curr_el = curr_substring[:match_start]
            results.append(curr_el)
            curr_substring = curr_substring[match_end:]

    return results
