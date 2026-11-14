# ADR-0008: Ephemeral AWS dev environment under a $20 monthly budget

- Status: accepted
- Date: 2026-11-13

## Context
Phase 2 deploys the wallet service to AWS (VPAY-34 Terraform, VPAY-35 CD). The owner wants to practise
production standards (infrastructure as code, private networking, keyless CI, automated delivery) on a
personal budget of **under USD 20 per month**, and expects to run the environment for **at most about 30 hours a
month**. [ADR-0007](https://github.com/vivid-pay/wallet-service/blob/develop/docs/adr/0007-private-dev-environment-before-security.md)
requires the dev environment to be private until the Security epic (VPAY-7) lands.

Always-on, the minimum useful stack (RDS PostgreSQL db.t4g.micro, Fargate 0.5 vCPU / 1 GB, a NAT gateway, an SSM
host) costs roughly USD 70 per month. Almost all of it is billed by the hour, so the cost follows the hours the
environment exists.

Prices (us-east-1, checked 2026-11-14 against third-party summaries of the AWS price lists; the official AWS
pricing pages did not return rates, so confirm in the AWS Pricing Calculator and the Budgets report):
RDS db.t4g.micro PostgreSQL about USD 0.016 per hour, gp3 storage about USD 0.115 per GB-month; NAT gateway
USD 0.045 per hour plus USD 0.045 per GB processed; Fargate x86 USD 0.04048 per vCPU-hour and USD 0.004445 per
GB-hour (Arm is about 20 percent lower), so 0.5 vCPU and 1 GB is about USD 0.025 per hour. NAT data processing is
new to the earlier estimate and is small for a dev environment, but it is not zero.

## Options considered
1. **Always-on environment.** Simple, but about USD 70 per month. Breaks the budget.
2. **Cheaper always-on (single EC2 with Docker Compose).** About USD 10 to 15, but it teaches little about the
   target production shape (managed database, containers on ECS, private networking).
3. **Ephemeral environment, created and destroyed on demand by Terraform, database kept as a snapshot.** About
   USD 8 per month at 30 hours. Keeps the production shape. Costs a roughly 10 minute wait per session, a more
   involved pipeline, and a discipline (and safeguards) against forgetting to destroy it.
4. **Always-on database, ephemeral everything else.** About USD 19 to 20. No restore wait, but no headroom under
   the budget for a feature that is used 30 hours a month.

## Decision
Option 3.

### Lifecycle
- A separate repository, `vivid-pay/infrastructure`, holds the Terraform and two **manually triggered** workflows:
  **apply** (create the dev environment) and **destroy** (take a final database snapshot, then remove it).
- The environment stays up until the owner runs destroy.
- **Apply** starts the ECS service on the latest image in ECR (or a tag passed in) and restores the database from
  the latest snapshot. The first apply, with no snapshot, starts with an empty database.
- **Destroy** keeps only the latest snapshot.
- Kept outside the destroyed stack: Terraform state (S3 with locking), ECR repositories, database snapshots and
  secrets.

### Delivery (dev)
- Each service repository owns its own CD. On every merge to `develop` it builds the image, pushes it to ECR
  tagged with the commit SHA, and, **if the environment is running**, updates the ECS service to it. If the
  environment is not running the deploy step is skipped with a clear message; the build still succeeds.
- Each service repository also has a manual workflow that deploys a chosen branch to dev.
- Terraform ignores the service's image tag after creation, so apply and CD do not overwrite each other.
- GitHub Actions authenticate to AWS with OIDC. Each service repository gets a role limited to its own ECR
  repository and ECS service. No long-lived AWS keys are stored.

### Network and access
- Private subnets, no load balancer, no public IP, no public DNS record, in line with ADR-0007. The owner reaches
  the service and database through an SSM port-forwarding session.

### Cost safeguards
- An AWS Budgets alert at USD 15 per month, emailed to the owner.
- A reminder when the environment has been up longer than the monthly hour allowance. Automatic teardown is not
  adopted; the owner wants control of the lifetime.

### Promotion model (recorded, not built yet)
- Images are built once and promoted by tag. A later workflow on `release/**` tags and pushes the staging
  candidate; a later manual workflow deploys a chosen tag to production. Neither environment may run before the
  exit condition of ADR-0007 is met, and neither fits this budget while running.

## Consequences
- Each session starts with a roughly 10 minute apply, dominated by the database restore.
- A forgotten environment costs about USD 70 per month; the budget alert is a required safeguard.
- A merge while the environment is down is not deployed. The image waits in ECR and is used by the next apply.
- Snapshots cost about USD 0.095 per GB-month and are cleaned up on destroy.
- Multi-AZ, autoscaling and WAF are not run; they may be written in Terraform behind a flag and checked with
  `terraform plan` only.
- Revisit when VPAY-7 lands (public access, staging, production) or when the budget or monthly hours change.
