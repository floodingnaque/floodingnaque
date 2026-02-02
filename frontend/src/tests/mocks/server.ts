/**
 * MSW Server Configuration
 *
 * Node.js server for MSW used in tests.
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

/**
 * MSW server instance for testing
 */
export const server = setupServer(...handlers);

export default server;
