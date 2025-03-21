import pandas as pd
data = \"\na,b,c,d\n1,2,3,4\n2,3,4,5\n\"
df = pd.read_csv(pd.compat.StringIO(data), index_col=False)\nprint(df)
