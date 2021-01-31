# Authors

*Updated on 2021-01-31.*

These people contributed to AMY:

* [pbanaszkiewicz](https://github.com/pbanaszkiewicz)
* [gvwilson](https://github.com/gvwilson)
* [chrismedrela](https://github.com/chrismedrela)
* [aditnryn](https://github.com/aditnryn)
* [wking](https://github.com/wking)
* maneesha sane
* [rbeagrie](https://github.com/rbeagrie)
* [fmichonneau](https://github.com/fmichonneau)
* [maneesha](https://github.com/maneesha)
* [sburns](https://github.com/sburns)
* [neon-ninja](https://github.com/neon-ninja)
* [staeff](https://github.com/staeff)
* [drio](https://github.com/drio)
* [marwahaha](https://github.com/marwahaha)
* [dependabot[bot]](https://github.com/apps/dependabot)
* [shapiromatron](https://github.com/shapiromatron)
* [shubhsingh594](https://github.com/shubhsingh594)
* Raniere Silva
* Erin Becker
* [carlosp420](https://github.com/carlosp420)
* [jduckles](https://github.com/jduckles)
* [cudevmaxwell](https://github.com/cudevmaxwell)
* [nikhilweee](https://github.com/nikhilweee)
* [prerit2010](https://github.com/prerit2010)
* [darshan95](https://github.com/darshan95)
* [askingalot](https://github.com/askingalot)
* Christopher Medrela
* Jonah Duckles
* [timtomch](https://github.com/timtomch)
* [tracykteal](https://github.com/tracykteal)

The list was generated using this Python script:

```python
import requests
URL = "https://api.github.com/repos/carpentries/amy/contributors?anon=1"
data = requests.get(URL).json()
contributors = [
    (c.get("name", c.get("login", "anonymous")), c.get("html_url")) for c in data
]
for login, url in contributors:
    if url:
        print(f'* [{login}]({url})')
    else:
        print(f'* {login}')
```
