// Fully synthetic fixture — every value here is fake and exists only to trip rules.
import * as cdk from 'aws-cdk-lib';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { CfnOutput, SecretValue } from 'aws-cdk-lib';

export class BadStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string) {
        super(scope, id);

        // R001: context lookup of a secret-named parameter
        const apiKey = ssm.StringParameter.valueFromLookup(this, '/example/service/api-key');

        // R001: fromLookup variant
        const dbPassword = ssm.StringParameter.fromLookup(this, '/example/db/password');

        // R004: plain-text secret value
        const secret = SecretValue.unsafePlainText('not-a-real-secret-value');

        // R005: output leaking a secret-named variable
        new CfnOutput(this, 'ApiKeyOutput', {
            value: apiKey,
        });

        // R006 (optional rule): secret-named parameter created as Type: String
        new ssm.StringParameter(this, 'Param', {
            parameterName: '/example/service/signing-key',
            stringValue: 'not-a-real-key-either',
        });
    }
}
