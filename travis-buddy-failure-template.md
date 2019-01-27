@{{pullRequestAuthor}},

Please review the following log and resolve any issues.  

{{#jobs}}

<a href="{{link}}">View log</a>

{{#scripts}}

<details>
  <summary>
    <strong>
     {{command}}
    </strong>
  </summary>

```
{{&contents}}
```

</details>

{{/scripts}}
{{/jobs}}

Thank you for your contribution.
