
#sc print(lldb.target)
#sc print(lldb.process)
#sc print(lldb.debugger)

#setting append target.exec-search-paths "."
#setting append target.debug-file-search-paths "."
setting set symbols.enable-external-lookup false
#setting set plugin.symbol-file.dwarf.ignore-file-indexes true
#setting set target.import-std-module false 

# last load andb
script import andb
script andb.Load()
