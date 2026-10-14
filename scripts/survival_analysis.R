# Run from the repository root. Uses the R survival package only.
library(survival)
d <- read.csv("outputs/local/cleaned_cohort.csv", stringsAsFactors = FALSE)
d <- d[d$survival_eligible, ]
d$age_cat <- factor(d$age_cat, levels = c("Young", "Middle-aged", "Older"))
d$sex <- factor(d$sex, levels = c("Female", "Male"))
d$cancer_site <- factor(d$cancer_site, levels = c("Brain", "Breast", "Liver", "Prostate"))
d$race <- relevel(factor(d$race), ref = "White")
write.csv(data.frame(cohort = c("survival all race", "survival known race"),
                     records = c(nrow(d), sum(d$race != "Unknown")),
                     suicide_events = c(sum(d$event), sum(d$event[d$race != "Unknown"]))),
          "outputs/survival_cohort_counts.csv", row.names = FALSE)

curves <- list()
five_year <- list()
logrank <- list()
for (variable in c("cancer_site", "race", "sex", "age_cat")) {
  f <- as.formula(paste("Surv(analysis_time, event) ~", variable))
  fit <- survfit(f, data = d)
  s <- summary(fit)
  curves[[variable]] <- data.frame(variable = variable, group = sub("^[^=]+=", "", as.character(s$strata)),
                                  months = s$time, survival = s$surv, lower = s$lower, upper = s$upper,
                                  n_risk = s$n.risk, n_event = s$n.event)
  fs <- summary(fit, times = 60)
  five_year[[variable]] <- data.frame(variable = variable, group = sub("^[^=]+=", "", as.character(fs$strata)),
                                    months = fs$time, survival = fs$surv, lower = fs$lower,
                                    upper = fs$upper, n_risk = fs$n.risk)
  lr <- survdiff(f, data = d)
  logrank[[variable]] <- data.frame(variable = variable, chisq = lr$chisq, df = length(lr$n) - 1,
                                    p_value = pchisq(lr$chisq, length(lr$n) - 1, lower.tail = FALSE))
}
write.csv(do.call(rbind, curves), "outputs/km_curves.csv", row.names = FALSE)
write.csv(do.call(rbind, five_year), "outputs/km_60months.csv", row.names = FALSE)
write.csv(do.call(rbind, logrank), "outputs/logrank_tests.csv", row.names = FALSE)

# Competing deaths treated as a separate transition rather than censoring.
d$multi_status <- factor(d$status, levels = c(0, 1, 2), labels = c("censored", "suicide", "other_death"))
aj <- survfit(Surv(analysis_time, multi_status) ~ cancer_site, data = d)
as <- summary(aj)
write.csv(data.frame(group = sub("^[^=]+=", "", as.character(as$strata)), months = as$time,
                     suicide_cif = as$pstate[, "suicide"], other_death_cif = as$pstate[, "other_death"]),
          "outputs/competing_risk_curves.csv", row.names = FALSE)

# Known-race sensitivity for regression avoids an Unknown level without events.
reg <- droplevels(d[d$race != "Unknown", ])
f <- Surv(analysis_time, event) ~ age_cat + sex + race + cancer_site
cox <- coxph(f, data = reg, ties = "efron", x = TRUE)
cs <- summary(cox)
write.csv(data.frame(term = rownames(cs$coefficients), hazard_ratio = cs$conf.int[, 1],
                     ci_low = cs$conf.int[, 3], ci_high = cs$conf.int[, 4],
                     p_value = cs$coefficients[, 5]), "outputs/cox_hazard_ratios.csv", row.names = FALSE)
ph <- cox.zph(cox)
write.csv(data.frame(term = rownames(ph$table), ph$table), "outputs/cox_ph_tests.csv", row.names = FALSE)
aft <- survreg(f, data = reg, dist = "weibull")
ac <- summary(aft)$table
ac <- ac[rownames(ac) != "Log(scale)", , drop = FALSE]
write.csv(data.frame(term = rownames(ac), time_ratio = exp(ac[, 1]),
                     ci_low = exp(ac[, 1] - 1.96 * ac[, 2]), ci_high = exp(ac[, 1] + 1.96 * ac[, 2]),
                     p_value = ac[, 4]), "outputs/aft_time_ratios.csv", row.names = FALSE)

# Quantify sensitivity to the zero-month approximation.
sens <- list()
for (zero_rule in c("0.5 months", "1 month", "exclude")) {
  dd <- reg
  if (zero_rule == "1 month") dd$analysis_time[dd$survival_months == 0] <- 1
  if (zero_rule == "exclude") dd <- dd[dd$survival_months > 0, ]
  fit <- coxph(f, data = dd)
  ci <- summary(fit)$conf.int
  sens[[zero_rule]] <- data.frame(zero_month_rule = zero_rule, records = nrow(dd),
                                  term = rownames(ci), hazard_ratio = ci[, 1], ci_low = ci[, 3], ci_high = ci[, 4])
}
write.csv(do.call(rbind, sens), "outputs/zero_month_sensitivity.csv", row.names = FALSE)
capture.output(sessionInfo(), file = "outputs/r_session_info.txt")
capture.output(summary(cox), summary(aft), ph, file = "outputs/survival_model_summary.txt")
cat("Survival analysis complete. These are exploratory results from the supplied outcome-sampled cohort.\n")
