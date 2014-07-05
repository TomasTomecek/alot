# -*- coding: utf-8 -*-

# Copyright (C) 2011-2012  Patrick Totzke <patricktotzke@gmail.com>
# This file is released under the GNU GPL, version 3 or a later revision.
# For further details see the COPYING file

import logging
import argparse

from alot.commands import Command, registerCommand
from alot.commands.globals import MoveCommand
from alot import buffers

MODE = 'folders'


@registerCommand(MODE, 'fold', forced={'visible': False}, help='fold folders')
@registerCommand(MODE, 'unfold', forced={'visible': True}, help='unfold folders')
class ChangeDisplaymodeCommand(Command):
    """fold or unfold folder"""
    repeatable = True

    def __init__(self, visible=None, **kwargs):
        """
        :param visible: unfold if `True`, fold if `False`, ignore if `None`
        :type visible: True, False, 'toggle' or None
        """
        self.visible = visible
        Command.__init__(self)

    def apply(self, ui):
        folder_buffer = ui.current_buffer
        current_folder = folder_buffer.get_current_folder()
        logging.debug('(un)folding folder %s' % (current_folder))

        # determine new display values for this message
        #if self.visible == 'toggle':
        #    visible = folder_buffer.is_collapsed(current_folder)
        #else:
        #    visible = self.visible

        # collapse/expand depending on new 'visible' value
        if self.visible is False:
            folder_buffer.collapse()
        elif self.visible is True:  # could be None
            folder_buffer.expand()
        folder_buffer.refresh()


@registerCommand(MODE, 'open', help='open folder or saved search')
class OpenFolderCommand(Command):
    """ open selected folder """
    def __init__(self, **kwargs):
        Command.__init__(self)

    def apply(self, ui):
        folder_buffer = ui.current_buffer
        current_folder = folder_buffer.get_current_folder()
        query = current_folder.get_query_string()
        logging.debug("Opening search buffer for '%s'", query)
        open_searches = ui.get_buffers_of_type(buffers.SearchBuffer)
        to_be_focused = None
        for sb in open_searches:
            if sb.querystring == query:
                to_be_focused = sb
        if to_be_focused:
            if ui.current_buffer != to_be_focused:
                ui.buffer_focus(to_be_focused)
            else:
                # refresh an already displayed search
                ui.current_buffer.rebuild()
                ui.update()
        else:
            ui.buffer_open(buffers.SearchBuffer(ui, query))


@registerCommand(MODE, 'move', help='move focus in search buffer',
                 arguments=[(['movement'], {
                     'nargs': argparse.REMAINDER,
                     'help': 'unread next, unread previous'})])
class MoveFocusCommand(MoveCommand):

    def apply(self, ui):
        logging.debug(self.movement)
        fbuffer = ui.current_buffer
        if self.movement == 'unread next':
            fbuffer.focus_next_unread()
        elif self.movement == 'unread previous':
            fbuffer.focus_previous_unread()
        else:
            MoveCommand.apply(self, ui)
        ui.current_buffer.refresh()


@registerCommand(MODE, 'mark_as_read', help='mark threads in selected folder as read')
class MarkFolderAsRead(Command):
    """ remove 'unread' tag from all threads in folder """
    def apply(self, ui):
        folder_buffer = ui.current_buffer
        current_folder = folder_buffer.get_current_folder()
        logging.debug('removing \'unread\' tag from folder %s', current_folder)
        current_folder.remove_unread_tags()
        # current_folder.refresh()
        folder_buffer.rebuild()
        # yes, we are refreshing whole buffer even though when we could
        # refresh only the single folder -- it's superfast, so we don't
        # care
        ui.update()
