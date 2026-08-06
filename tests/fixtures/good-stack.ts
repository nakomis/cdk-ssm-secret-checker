// Fully synthetic fixture — clean patterns that must NOT trip any rule.
import * as cdk from 'aws-cdk-lib';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as route53 from 'aws-cdk-lib/aws-route53';
import { CfnOutput, SecretValue } from 'aws-cdk-lib';

export class GoodStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string) {
        super(scope, id);

        // Deploy-time reference — value never lands in cdk.context.json
        const apiKey = ssm.StringParameter.valueForStringParameter(this, '/example/service/api-key');

        // Non-secret lookup is fine
        const logLevel = ssm.StringParameter.valueFromLookup(this, '/example/service/log-level');

        // Hosted-zone lookups cache non-secret context
        const zone = route53.HostedZone.fromLookup(this, 'Zone', { domainName: 'example.test' });

        // Secrets Manager reference — resolved at deploy time
        const secret = SecretValue.secretsManager('example-secret-name');

        // Output of a non-secret value
        new CfnOutput(this, 'BucketName', {
            value: 'example-bucket-name',
        });

        // Non-secret parameter as Type: String is fine even with R006 on
        new ssm.StringParameter(this, 'Param', {
            parameterName: '/example/service/log-level',
            stringValue: 'info',
        });
    }
}
