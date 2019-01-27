@{{pullRequestAuthor}},

Please review the following log and address any suggestions.  

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
