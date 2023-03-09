A one-off script to clean up old vercel deployments.

Script assumes that you have the vercel-cli and that it is "switched"

to the team owning the project in question.

vercel-cli should already be "team switched", ie:

`$ vercel teams switch my_team_name`

## configuration:

  set the values for PROJECT and AGE as desired.

## use:

1) list deployments without destroying.

`$ ./vercel_prune.py`

2) destroy deployments older than `AGE`

`$ ./vercel_prune.py remove`

## warning:

The vercel API will fail at random times with some regularity.
It's not your fault. You may repeat the operation.

```
(Deployment[], stderr) = ls(project)
Deployment[] = ls_all(project)
(stdout, stderr) = remove(Deployment)

bool = Deployment.is_state(DeploymentState)
bool = Deployment.older_than(str|int) # "50d" | 50 * 86400
```
