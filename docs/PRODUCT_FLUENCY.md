# Product Fluency v0.8

Writing output rate is `normalized word count / (actual active-writing seconds / 60)`. It is calculated only for timed writing with a positive actual duration, accepted timing quality, acceptable text input, and no unexplained interruption.

`time_limit_minutes` is a task ceiling and is never substituted for actual duration. Missing duration produces `null`/`insufficient_data`; a 45-minute limit therefore cannot create WPM. Source, quality, start/submission timestamps, active duration, word count, formula inputs, and limitations are retained. WPM is a descriptive production-condition proxy, not a fluency-ability, quality, or speed score.
