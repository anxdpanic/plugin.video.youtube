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

try:
    from ....kodion import logger
except:
    class logger:
        @staticmethod
        def log_debug(txt):
            print(txt)


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


def throttling_splice(d, e):
    """Splices array 'd' with remapped start index e.
    From this code: function(d,e){e=(e%d.length+d.length)%d.length;d.splice(e,1)}
    """
    e = throttling_mod_func(d, e)
    return js_splice(d, e, 1)


class CalculateN:
    # References:
    # https://github.com/ytdl-org/youtube-dl/issues/29326#issuecomment-894619419
    # https://github.com/pytube/pytube/blob/fc9aec5c35829f2ebb4ef8dd599b14a666850d20/pytube/cipher.py

    # To maintainers: it might be necessary to add more function patterns (and implementations)
    # in the future as the "base.js" player code gets changed and updated.
    MAPPING_FUNC_PATTERNS = (
        (r"{for\(\w=\(\w%\w\.length\+\w\.length\)%\w\.length;\w--;\)\w\.unshift\(\w.pop\(\)\)}", throttling_unshift),  # noqa:E501
        (r"{\w\.reverse\(\)}", throttling_reverse),
        (r"{\w\.push\(\w\)}", throttling_push),
        (r";var\s\w=\w\[0\];\w\[0\]=\w\[\w\];\w\[\w\]=\w}", throttling_swap),
        (r"case\s\d+", throttling_cipher_function),
        (r"\w\.splice\(0,1,\w\.splice\(\w,1,\w\[0\]\)\[0\]\)", throttling_nested_splice),  # noqa:E501
        (r";\w\.splice\(\w,1\)}", throttling_splice),
        (r"\w\.splice\(-\w\)\.reverse\(\)\.forEach\(function\(\w\){\w\.unshift\(\w\)}\)", throttling_prepend),  # noqa:E501
        (r"for\(var \w=\w\.length;\w;\)\w\.push\(\w\.splice\(--\w,1\)\[0\]\)}", throttling_reverse),  # noqa:E501
    )

    def __init__(self, js):
        self.calculated_n = None
        self.mutable_n_list = []

        raw_code = self.get_throttling_function_code(js).replace('\n', '')
        self.throttling_plan = self.get_throttling_plan(raw_code)
        self.throttling_array = self.get_throttling_function_array(self.mutable_n_list, raw_code)


    @staticmethod
    def get_throttling_function_code(js):
        """Extract the raw code for the throttling function.
        :param str js:
            The contents of the base.js asset file.
        :rtype
        :returns:
            The full string code of the function, in the form "...=function(...){...};"
            Note: might include whitespace in the body of the function.
        """

        # Only present in the throttle function code.
        fiduciary_index = js.find('enhanced_except_')
        if fiduciary_index == -1:
            logger.log_debug('ratebypass: fiduciary_index not found')
            return ''

        start_index = js.rfind('=function(', 0, fiduciary_index)
        start_index = js.rfind(';', 0, start_index)
        if start_index == -1:
            logger.log_debug('ratebypass: function code start not found')
            return ''
        else:
            # Skip the semicolon that this index points to.
            start_index += 1

        end_pattern = '};'
        end_index = js.find(end_pattern, fiduciary_index)
        if end_index == -1:
            logger.log_debug('ratebypass: function code end not found')
            return ''
        else:
            # Skip ahead to include the end pattern in the output string.
            end_index += len(end_pattern)

        return js[start_index:end_index].strip()


    @staticmethod
    def get_throttling_plan(raw_code):
        """Extract the "throttling plan".
        The "throttling plan" is the list of commands executed to unscramble the n value.
        These commands reference items from the "c" array.
        :param str raw_code:
            The response from get_throttling_function_code(js).
        :returns:
            A list of tuples, where the first element of each tuple is the
            index of the function to call, the remaining elements are arguments to
            pass to that function.
        """

        plan_start_pattern = r"try{"
        plan_start_index = raw_code.find(plan_start_pattern)
        if plan_start_index == -1:
            logger.log_debug('ratebypass: command block start not found')
            return
        else:
            # Skip the whole start pattern, it's not needed.
            plan_start_index += len(plan_start_pattern)

        plan_end_pattern = '}'
        plan_end_index = raw_code.find(plan_end_pattern, plan_start_index)
        if plan_end_index == -1:
            logger.log_debug('ratebypass: command block end not found')
            return

        plan_raw = raw_code[plan_start_index:plan_end_index]

        # So far, these commands are either c[x](c[y]) or c[x](c[y],c[z]).
        return [
            # The following will split a single command of the form
            # "c[x](c[y], c[z], ...)" into ['x', 'y', 'z', ...], then convert it
            # to a tuple of ints.
            tuple(map(int, command[:-1].replace('c[', '').replace(']', '')
                           .replace('(', ',').split(',')))
            for command in plan_raw.split('),')
        ]


    @staticmethod
    def array_reverse_split_gen(raw_array):
        """ Iterates the comma-split pieces of the stringified list in reverse,
            joining pieces that are part of the same longer object that might
            have comma characters inside.
        :param str raw_array:
            The "c" array string, without enclosing brackets.
        :returns:
            Generates the elements of the stringified array in REVERSE order.
            The caller is responsible for reversing it back to normal.
        """
        accumulator = None
        for piece in reversed(raw_array.split(',')):
            if piece.startswith('function') or piece[0] == '"' or piece[0] == "'":
                # When the piece starts with "function" or a quote char, yield
                # what has been accumulated so far, if anything.
                if accumulator:
                    yield piece + ',' + accumulator
                    accumulator = None
                else:
                    yield piece
            elif piece.endswith('}') or piece[-1] == '"' or piece[-1] == "'":
                # When the piece ends with a curly bracket or quote char but
                # didn't start with "function" or a quote char, start
                # accumulating with the next pieces until it's closed.
                accumulator = piece
            else:
                if accumulator:
                    accumulator = piece + ',' + accumulator
                else:
                    yield piece


    @classmethod
    def get_throttling_function_array(cls, mutable_n_list, raw_code):
        """Extract the "c" array that comes with values and functions
        used to unscramble the initial n value.
        :param list mutable_n_list:
            Mutable list with the characters of the "initial n" value.
        :param str raw_code:
            The response from get_throttling_function_code(js).
        :returns:
            The array of various integers, arrays, and functions.
        """

        array_start_pattern = ",c=["
        array_start_index = raw_code.find(array_start_pattern)
        if array_start_index == -1:
            logger.log_debug('ratebypass: "c" array pattern not found')
            return [ ]
        else:
            array_start_index += len(array_start_pattern)

        array_end_pattern = '];'
        array_end_index = raw_code.rfind(array_end_pattern)
        if array_end_index == -1:
            logger.log_debug('ratebypass: "c" array end not found')
            return [ ]

        raw_array = raw_code[array_start_index:array_end_index]
        str_array = tuple(cls.array_reverse_split_gen(raw_array))[::-1]
        #logger.log_debug('STR_ARRAY:\n' + '\n'.join(str(i)+' >'+c+'<' for i,c in enumerate(str_array))+'\n\n')

        converted_array = [ ]

        for el in str_array:
            try:
                converted_array.append(int(el))
                continue
            except ValueError:
                # Not an integer value.
                pass

            if el == 'null':
                # As per the JavaScript, replace null elements in this array
                # with a reference to itself.
                converted_array.append(converted_array)
                continue

            if el[0] == '"' and el[-1] == '"':
                # Convert e.g. '"abcdef"' to string without quotation marks, 'abcdef'
                converted_array.append(el.strip('\'"'))
                continue

            if el.startswith('function'):
                found = False
                for pattern, fn in cls.MAPPING_FUNC_PATTERNS:
                    if re.search(pattern, el):
                        converted_array.append(fn)
                        found = True
                        break
                else:
                    logger.log_debug('ratebypass: mapping function not yet listed: {unknown_func}'
                                     .format(unknown_func=el))
                if found:
                    continue

            # Probably the single "b" references (references to a list with the
            # initial 'n' characters).
            converted_array.append(mutable_n_list)

        return converted_array


    def calculate_n(self, initial_n_list):
        """Converts n to the correct value to prevent throttling.
        :param list initial_n_list:
            A list with the characters of the initial "n" string.
        :returns:
            The new value of "n" as a string, to replace the initial "n" in the
            video stream URL.
        """
        if self.calculated_n:
            logger.log_debug('`n` already calculated: {calculated_n}. returning early...'
                             .format(calculated_n=self.calculated_n))
            return self.calculated_n

        if not self.throttling_plan or not self.throttling_array:
            return None

        initial_n_string = ''.join(initial_n_list)
        logger.log_debug('Attempting to calculate `n` from initial: {initial_n}'
                         .format(initial_n=initial_n_string))

        # Clear (in-place) and refill this list with the characters from 'initial_n_list'.
        # Note that references to this list are already in self.throttling_array.
        del self.mutable_n_list[:] # https://stackoverflow.com/a/30087221
        self.mutable_n_list.extend(initial_n_list)

        # For each step in the plan, get the first item of the step as the
        # index of the function to call, and then call that function using
        # the throttling array elements indexed by the remaining step items.
        try:
            for step in self.throttling_plan:
                step_iter = iter(step)
                curr_func = self.throttling_array[next(step_iter)]
                if not callable(curr_func):
                    logger.log_debug('{curr_func} is not callable.'.format(curr_func=curr_func))
                    logger.log_debug('Throttling array:\n{throttling_array}\n'
                                     .format(throttling_array=self.throttling_array))
                    return None
                # Execute the command function.
                args = (self.throttling_array[i] for i in step_iter)
                curr_func(*args)

            self.calculated_n = ''.join(self.mutable_n_list)
        except:
            logger.log_debug('Error calculating new `n`, reusing input')
            return initial_n_string

        self.calculated_n = ''.join(self.mutable_n_list)
        logger.log_debug('Calculated `n`: {calculated_n}'
                         .format(calculated_n=self.calculated_n))
        return self.calculated_n
