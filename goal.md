# store english word and meaning in json

- every time I use youdao_translation function successfully, now I want to store the english word to local json file
- notice I need to store data when I lookup english word, sometime I look up Chinese which do not need to store

use following code to detect the json path

```
if getattr(sys, 'frozen', False):
    base_path = Path(sys.executable).parent.parent
else:
    base_path = Path(__file__).resolve().parent.parent
```
