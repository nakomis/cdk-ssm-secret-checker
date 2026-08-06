// Fully synthetic fixture — violations silenced by cssc:ignore directives.
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { SecretValue } from 'aws-cdk-lib';

// cssc:ignore
const a = ssm.StringParameter.valueFromLookup(this, '/example/legacy/api-key');

const b = ssm.StringParameter.valueFromLookup(this, '/example/legacy/token'); // cssc:ignore R001

// cssc:ignore R004
const c = SecretValue.unsafePlainText('placeholder-for-tests');

// Wrong rule listed — this one must still be reported
const d = SecretValue.unsafePlainText('also-a-placeholder'); // cssc:ignore R001
