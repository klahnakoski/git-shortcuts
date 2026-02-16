# More GIT

Some git shortcuts


### Safe checkout

Quickly checkout a branch without worrying about losing work. This is especially useful when you have a lot of uncommitted changes, and you want to switch to another branch to work on something else, but you don't want to lose your changes.

```commandline
hit checkout <branch>
```

### Merge without conflicts

Quickly merge a branch without worrying about conflicts.  Conflicted files will be added to the repo with the foreign branch name appended to the filename.  You can resolve conflicts later by comparing the files and selecting the changes you want to keep.

```commandline
hit merge <branch>
```

### Alias branch names

Corporate repositories often have long branch names that are difficult to remember and type.  You can create aliases for these branch names to make it easier to work with them.

```commandline
hit alias <branch> as <alias> 
```

you can also do this during checkout:

```commandline
hit checkout [-bB] <branch> as <alias>
```


