# left mouse click the tray pop up loopup history window

now the word_store is like:

```
[
  {
    "query": "list",
    "results": "list: n. 列表，清单；（船）倾侧；围栏；（织物的）镶边；<旧>渴望，喜好；（尤指按重要程度排列的）事物清...\nlisten: v. 听，倾听；听从，听信；努力听，留神地听（listen for/listen out for）；...",
    "lookup_count": 2
  },
  {
    ...
  }
  ...
]
```

when I left mouse click the tray, than pop up a windows show the english word lookup history in a flash card format

the window:
- load the json file every time pop up
- the shown order of words is random
- the layout is like 
  - top panel (show how many words stored, a `random` button, I click it, the order of words will be random again)
  - show word area with query, results and lookup_count
  - bottom panel, just a simple right and left arrow, I click it flash show next or previous word card

pyqtSignal should init in class level, do not put in the `__init__` function
