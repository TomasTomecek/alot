# -*- coding: utf-8 -*-

import os
import logging
import datetime
from collections import OrderedDict

from alot.db.manager import DBManager
from alot.settings import settings
from alot.oswalk import walk


class Folder(object):
    """ wrappar on top of notmuch query for a folder """

    def __init__(self, dbman, folder_name, rel_path):
        self.dbman = dbman
        self.folder_name = folder_name
        self.query_folder_name = rel_path if not rel_path.startswith('/') else rel_path[1:]
        # notmuch <1.7 syntax:
        #   folder:"folder.subfolder"
        # notmach >=1.7 syntax:
        #   folder:folder/.subfolder ('folder: ' find something, 'folder: ""' does not)
        # FIXME: either warn users and force them use nm-1.7+, or support both
        self.query = 'folder:"%s"' % self.query_folder_name
        self.new_query = 'folder:"%s" tag:unread' % self.query_folder_name
        self.count = 0
        self.refresh()

    def __str__(self):
        return "[%d] %s" % (self.count, self.folder_name)

    def __unicode__(self):
        return unicode(self.__str__())

    def __repr__(self):
        return "Folder([%d] %s (%s))" % (self.count, self.folder_name, self.query)

    def get_id(self):
        return self.query_folder_name

    def get_query_string(self):
        return self.query

    def remove_unread_tags(self):
        self.dbman.untag(self.new_query, ['unread'])
        self.dbman.flush()

    def refresh(self):
        self.count = self.dbman.count_messages(self.new_query)
        return self.count


class SavedSearch(object):
    """ Saved query: wrapper on top of notmuch query """

    def __init__(self, dbman, query):
        self.dbman = dbman
        self.folder_name = query
        self.query = query
        self.new_query = query + ' tag:unread'
        self.count = 0
        self.refresh()

    def __str__(self):
        return "[%d] %s" % (self.count, self.folder_name)

    def __repr__(self):
        return self.__str__()

    def get_id(self):
        return self.query

    def get_query_string(self):
        return self.query

    def refresh(self):
        self.count = self.dbman.count_messages(self.new_query)
        return self.count


class Account(object):
    """
    represents IMAP account with folders
    """

    def __init__(self, dbman, account_path, saved_searches=None, blacklist_folders=None):
        """
        :param dbman: db manager that is used for further lookups
        :type dbman: :class:`~alot.db.DBManager`
        """
        self._dbman = dbman
        #list of folders to blacklist
        self.blacklist_folders = ['tmp', 'new', 'cur']
        if blacklist_folders:
            self.blacklist_folders += blacklist_folders
        self.account_path = os.path.abspath(os.path.expanduser(account_path))
        self.saved_searches = saved_searches
        self._init_vars()

        # TODO: there could something more interesting in a label of a root folder here
        self.root_folder = Folder(self._dbman, settings.get_main_addresses()[0], '')

    def _init_vars(self):
        """ initiate variables """
        # list of paths
        self._folders_list = []
        # mapping between rel_path and class Folder
        self._folder_mapping = {}
        # class Folder -> children
        self._folders = OrderedDict()
        self._saved_search_folders = []
        self._unread_folders = []

    def get_fs_folders(self):
        """
        find imap folders on filesystem and create hierarchy out of it
        """
        n = datetime.datetime.now()
        all_dirs = walk(self.account_path, ignore_dirs=self.blacklist_folders)
        for d in all_dirs:
            basename = d.rsplit('/', 1)[1]
            # make it relative
            rel_d = d[len(self.account_path):]
            # strip leading slash
            rel_d = rel_d[1:] if rel_d.startswith('/') else rel_d
            # ignore dot folders -- probably notmuch stuff
            if rel_d and not rel_d.startswith('.'):
                self._folders_list.append((rel_d, basename))
        # TODO: make this configurable
        self._folders_list = sorted(self._folders_list, key=lambda y: y[0].lower())
        logging.debug("Imap folders lookup took %s", datetime.datetime.now() - n)

    def get_root(self):
        return self.root_folder

    def get_folder(self, rel_path):
        """ return folder specified via relative path """
        return self._folder_mapping[rel_path]

    def get_children(self, folder):
        try:
            return self._folders[folder]
        except KeyError:
            return []

    def get_folders_count(self):
        return len(self._folders)

    def get_saved_searches_count(self):
        return sum([x.count for x in self._saved_search_folders])

    def get_next_unread(self, folder):
        try:
            index = self._unread_folders.index(folder)
        except ValueError:
            return self._unread_folders[0]
        try:
            return self._unread_folders[index + 1]
        except IndexError:
            return self._unread_folders[0]

    def get_previous_unread(self, folder):
        try:
            index = self._unread_folders.index(folder)
        except ValueError:
            return self._unread_folders[0]
        try:
            return self._unread_folders[index - 1]
        except IndexError:
            return self._unread_folders[-1]

    def get_folders(self):
        """
        process folders and searches by querying notmuch
        """
        if not self._folders:  # if not already cached
            self._folders[self.root_folder] = []
            # make inbox first
            inbox_list = [(index, item) for index, item in enumerate(self._folders_list)
                          if item[1].lower() == 'inbox']
            try:
                index, inbox = inbox_list[0]
            except IndexError:
                pass
            else:
                f = Folder(self._dbman, inbox[1], inbox[0])
                del self._folders_list[index],
                self._folders.setdefault(f, [])
                self._folder_mapping[inbox[0]] = f
                self._folders[self.root_folder].append(f)

            for rel_path, basename in self._folders_list:
                nice_name = basename[1:] if basename.startswith(".") else basename
                f = Folder(self._dbman, nice_name, rel_path)
                self._folders.setdefault(f, [])
                self._folder_mapping[rel_path] = f

                parent_path = rel_path.rsplit('/', 1)[0]
                if parent_path == rel_path:
                    self._folders[self.root_folder].append(f)
                else:
                    self._folders[self.get_folder(parent_path)].append(f)
                if f.count > 0:
                    self._unread_folders.append(f)

            if self.saved_searches:
                for parent_folder_path, queries in self.saved_searches:
                    for query in queries:
                        try:
                            parent_folder = self.get_folder(parent_folder_path)
                        except KeyError:
                            logging.warning("Folder '%s' for saved search '%s' not found.",
                                            parent_folder_path, query)
                            continue
                        saved_search = SavedSearch(self._dbman, query)
                        self._folders[parent_folder].append(saved_search)
                        self._saved_search_folders.append(saved_search)
        return self._folders

    def refresh(self):
        """ refresh thread metadata from the index """
        self._init_vars()
        self.get_fs_folders()
        return self.get_folders()

    def __str__(self):
        return "Account"


if __name__ == '__main__':
    import sys
    from pprint import pprint
    p = sys.argv[1]
    dbman = DBManager(path=p, ro=True)
    a = Account(dbman, p)
    a.get_folders()
    folders = a.get_folders()
    pprint(folders)
