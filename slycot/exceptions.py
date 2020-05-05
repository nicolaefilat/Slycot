"""
exceptions.py

Copyright 2020 Slycot team

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301, USA.
"""

import re


class SlycotError(RuntimeError):
    """Slycot exception base class"""

    def __init__(self, message, info):
        super(SlycotError, self).__init__(message)
        self.info = info


class SlycotParameterError(SlycotError, ValueError):
    """A Slycot input parameter had an illegal value.

    In case of a wrong input value, the SLICOT routines return a negative
    info parameter indicating which parameter was illegal.
    """

    pass


class SlycotArithmeticError(SlycotError, ArithmeticError):
    """A Slycot computation failed"""

    pass


def raise_if_slycot_error(info, arg_list=None, docstring=None, checkvars={}):
    """Raise exceptions if slycot info returned is non-zero.

    Parameters
    ----------
    info: int
        The parameter INFO returned by the SLICOT subroutine
    arg_list: list of str, optional
        A list of arguments (possibly hidden by the wrapper) of the SLICOT
        subroutine
    docstring: str, optional
        The docstring of the Slycot function
    checkvars: dict, optional
        dict of variables for evaluation of <infospec> and formatting the
        exception message

    Notes
    -----
    If the numpydoc compliant docstring has a "Raises" section with one or
    multiple definition terms ``SlycotError : e`` or a subclass of it,
    the matching exception text is used.

    The definition body must contain a reST compliant field list with
    ':<infospec>:' as field name, where <infospec> specifies the valid values
    for `e.ìnfo` in a python parseable expression using the variables provided
    in `checkvars`. A single " = " is treated as " == ".

    The body of the field list contains the exception message and can contain
    replacement fields in format string syntax using the variables in
    `checkvars`.

    For negative info, the argument as indicated in arg_list was erroneous and
    a generic SlycotParameterError is raised if no custom text was defined in
    the docstring or no docstring is provided.

    Example
    -------
    >>> def fun(info):
    ...     \"""Example function
    ...
    ...     Raises
    ...     ------
    ...     SlycotArithmeticError : e
    ...         :e.info = 1: Info is 1
    ...         :e.info > 1 and e.info < n:
    ...             Info is {e.info}, which is between 1 and {n}
    ...         :n <= e.info < m:
    ...             {e.info} is between {n} and {m:10.2g}!
    ...     \"""
    ...     n, m = 4, 1.2e2
    ...     raise_if_slycot_error(info,
    ...                           arg_list=["a", "b", "c"],
    ...                           docstring=fun.__doc__,
    ...                           checkvars=locals())
    ...
    >>> fun(0)
    >>> fun(-1)
    SlycotParameterError: The following argument had an illegal value: a
    >>> fun(1)
    SlycotArithmeticError: Info is 1
    >>> fun(2)
    SlycotArithmeticError: Info is 2, which is between 1 and 4
    >>> fun(5)
    SlycotArithmeticError: 4 is between 4 and    1.2e+02!
    """
    if docstring:
        slycot_error_map = {"SlycotError": SlycotError,
                            "SlycotParameterError": SlycotParameterError,
                            "SlycotArithmeticError": SlycotArithmeticError}

        docline = iter(docstring.splitlines())
        info_eval = False
        try:
            while "Raises" not in next(docline):
                continue

            section_indent = next(docline).index("-")

            slycot_error = None
            for l in docline:
                print(l)
                # ignore blank lines
                if not l.strip():
                    continue


                # reached end of Raises section without match
                if not l[:section_indent].isspace():
                    return None

                # Exception Type
                ematch = re.match(
                    r'(\s*)(Slycot(Parameter|Arithmetic)?Error) : e', l)
                if ematch:
                    error_indent = len(ematch[1])
                    slycot_error = ematch[2]

                # new infospec
                if slycot_error:
                    imatch = re.match(
                        r'(\s{' + str(error_indent + 1) + r',}):(.*):\s*(.*)',
                        l)
                    if imatch:
                        infospec_indent = len(imatch[1])
                        infospec = imatch[2]
                        # Don't handle the standard case unless we have i
                        if infospec == "e.info = -i":
                            if 'i' not in checkvars.keys():
                                continue
                        infospec_ = infospec.replace(" = ", " == ")
                        checkvars['e'] = SlycotError("", info)
                        try:
                            info_eval = eval(infospec_, checkvars)
                        except NameError:
                            raise RuntimeError("Unknown variable in infospec: "
                                               + infospec)
                        except SyntaxError:
                            raise RuntimeError("Invalid infospec: "
                                               + infospec)
                        if info_eval:
                            message = imatch[3].strip() + '\n'
                            mmatch = re.match(
                                r'(\s{' + str(infospec_indent+1) + r',})(.*)',
                                next(docline))
                            if not mmatch:
                                break  # docstring
                            body_indent = len(mmatch[1])
                            message += mmatch[2] + '\n'
                            for l in docline:
                                if l and not l[:body_indent].isspace():
                                    break  # message body
                                message += l[body_indent:] + '\n'
                            break  # docstring
        except StopIteration:
            pass
        if info_eval and message:
            fmessage = '\n' + message.format(**checkvars).strip()
            raise slycot_error_map[slycot_error](fmessage, info)

    if info < 0 and arg_list:
        message = ("The following argument had an illegal value: {}"
                   "".format(arg_list[-info-1]))
        raise SlycotParameterError(message, info)
